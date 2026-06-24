"""出题路由。

POST /api/documents/{id}/generate-quiz：两步生成 + 简化自评，
落库 Concepts/Questions，新建 QuizSession（status=in_progress），返回生成结果。

切片 1.1 请求内同步出题（mock LLM 秒级；真实 LLM 耗时留给切片 1.2 的参数控制与进度）。
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_llm_client, get_session
from quizcraft.models.document import Concept, Document, Section
from quizcraft.models.quiz import Question, QuestionType, QuizSession, SessionStatus
from quizcraft.schemas.quiz import (
    ConceptOut,
    QuestionOut,
    QuizGenerationRequest,
    QuizGenerationResponse,
    QuizSessionOut,
)
from quizcraft.services.llm import LLMClient
from quizcraft.services.quiz import filter_sections_by_scope, generate_quiz

router = APIRouter(prefix="/api/documents", tags=["quiz"])

# 子系统3：支持选择题与简答题；判断/填空留后续（评分方式绑定）
SUPPORTED_QUESTION_TYPES = {
    QuestionType.MULTIPLE_CHOICE.value,
    QuestionType.SHORT_ANSWER.value,
}


@router.post("/{document_id}/generate-quiz", response_model=QuizGenerationResponse, status_code=201)
async def generate_quiz_for_document(
    document_id: int,
    body: QuizGenerationRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm_client),
) -> QuizGenerationResponse:
    """对文档执行两步出题 + 自评，落库并返回新答题会话。

    子系统2：可选 body 传入出题参数（number/difficulty_range/question_types/
    chapter_scope/bloom_distribution）；无 body 时退回默认（切片 1.1 行为）。
    """
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    result = await session.execute(
        select(Section)
        .where(Section.document_id == document_id)
        .order_by(Section.order_index)
    )
    sections = result.scalars().all()
    if not sections:
        raise HTTPException(status_code=400, detail="文档无可出题的分块")

    params = body or QuizGenerationRequest()

    # question_types 校验（调 LLM 前，避免无谓出题）
    if params.question_types:
        unsupported = set(params.question_types) - SUPPORTED_QUESTION_TYPES
        if unsupported:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"暂不支持题型: {sorted(unsupported)}（当前支持 multiple_choice / short_answer；"
                    "判断/填空留待后续子系统）"
                ),
            )

    # chapter_scope 按 section_path 子串过滤出题范围
    sections = filter_sections_by_scope(sections, params.chapter_scope)
    if not sections:
        raise HTTPException(status_code=400, detail="章节范围内无可出题的分块")

    # 子系统6：未指定 self_eval_threshold 时不传 → generate_quiz 用默认 2/3（启用自评）；
    # 用户显式传值时覆盖（0=保留全部题不淘汰但仍自评记分，调高则更严格淘汰）
    gen_kwargs: dict = dict(
        concepts_per_section=params.concepts_per_section,
        questions_per_concept=params.questions_per_concept,
        number=params.number,
        difficulty_range=params.difficulty_range,
        question_types=params.question_types,
        bloom_distribution=params.bloom_distribution,
    )
    if params.self_eval_threshold is not None:
        gen_kwargs["self_eval_threshold"] = params.self_eval_threshold
    gen = await generate_quiz(sections, llm, **gen_kwargs)

    # 落库 Concepts（保留 ORM 引用，供 Question 外键与响应回填）
    concept_orm: list[Concept] = []
    for gc in gen.concepts:
        section = sections[gc.section_index]
        concept = Concept(
            document_id=document_id,
            section_id=section.id,
            name=gc.name,
            description=gc.description,
            source_span=gc.source_span,
            bloom_level=gc.bloom_level,
        )
        session.add(concept)
        await session.flush()
        concept_orm.append(concept)

    # 落库 Questions（按题型落对应字段：选择题 options/correct_option_index，简答题 answer_text）
    question_orm: list[Question] = []
    for gq in gen.questions:
        section = sections[gq.section_index]
        concept_id = (
            concept_orm[gq.concept_index].id
            if gq.concept_index < len(concept_orm)
            else None
        )
        question = Question(
            document_id=document_id,
            concept_id=concept_id,
            section_id=section.id,
            question_type=QuestionType(gq.question_type),
            stem=gq.stem,
            options=gq.options,
            correct_option_index=gq.correct_option_index,
            answer_text=gq.answer_text,
            explanation=gq.explanation,
            source_span=gq.source_span,
            bloom_level=gq.bloom_level,
            difficulty=gq.difficulty,
            self_eval_score=gq.self_eval_score,
        )
        session.add(question)
        await session.flush()
        question_orm.append(question)

    # 新建 QuizSession（in_progress，答完由答题子系统置 completed）
    quiz = QuizSession(
        document_id=document_id,
        question_ids=[q.id for q in question_orm],
        status=SessionStatus.IN_PROGRESS,
        total=len(question_orm),
    )
    session.add(quiz)
    await session.flush()
    await session.commit()
    await session.refresh(quiz)

    return QuizGenerationResponse(
        quiz_session=QuizSessionOut.model_validate(quiz),
        questions=[QuestionOut.model_validate(q) for q in question_orm],
        concepts=[ConceptOut.model_validate(c) for c in concept_orm],
    )


__all__ = ["router"]
