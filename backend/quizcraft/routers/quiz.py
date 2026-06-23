"""出题路由。

POST /api/documents/{id}/generate-quiz：两步生成 + 简化自评，
落库 Concepts/Questions，新建 QuizSession（status=in_progress），返回生成结果。

切片 1.1 请求内同步出题（mock LLM 秒级；真实 LLM 耗时留给切片 1.2 的参数控制与进度）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_llm_client, get_session
from quizcraft.models.document import Concept, Document, Section
from quizcraft.models.quiz import Question, QuestionType, QuizSession, SessionStatus
from quizcraft.schemas.quiz import (
    ConceptOut,
    QuestionOut,
    QuizGenerationResponse,
    QuizSessionOut,
)
from quizcraft.services.llm import LLMClient
from quizcraft.services.quiz import generate_quiz

router = APIRouter(prefix="/api/documents", tags=["quiz"])


@router.post("/{document_id}/generate-quiz", response_model=QuizGenerationResponse, status_code=201)
async def generate_quiz_for_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm_client),
) -> QuizGenerationResponse:
    """对文档执行两步出题 + 自评，落库并返回新答题会话。"""
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

    gen = await generate_quiz(sections, llm)

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

    # 落库 Questions
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
            question_type=QuestionType.MULTIPLE_CHOICE,
            stem=gq.stem,
            options=gq.options,
            correct_option_index=gq.correct_option_index,
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
