"""答题路由：POST /api/quiz-sessions/{id}/answer —— 按题型分流判分/评分 + LLM 引用原文反馈。

切片 1.1 选择题 + 切片 1.2 子系统3 简答题：
- 选择题：selected_option_index 确定性判分（不依赖 LLM），LLM 生成引用原文反馈。
- 简答题：short_answer_text 经 LLM rubric 评分 0-1 + 引用文档反馈；空响应/异常走兜底（不 500）。
- 同一会话+题目重答幂等（更新而非新增 Answer），便于改答案。
- 答完全部题目后置 status=completed + score（选择题按 is_correct 计 1，简答题按 score 计分）。
  混合会话 score = (选择题正确数 + 简答题分数和) / 总题数。

LLM 全程可 mock。answer 不在出题 router（prefix /api/documents）下，故独立成路由。
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_llm_client, get_session
from quizcraft.models.flashcard import Flashcard, FlashcardOrigin, FlashcardPriority
from quizcraft.models.quiz import Answer, Question, QuestionType, QuizSession, SessionStatus
from quizcraft.schemas.quiz import AnswerOut, AnswerRequest
from quizcraft.services.llm import LLMClient
from quizcraft.services.quiz.feedback import generate_feedback
from quizcraft.services.quiz.fill_blank import score_fill_blank
from quizcraft.services.quiz.short_answer import score_short_answer

router = APIRouter(prefix="/api/quiz-sessions", tags=["quiz"])


def _correct_answer_text(question: Question) -> str:
    """Return a user-facing correct answer string for a flashcard back."""
    if question.question_type == QuestionType.MULTIPLE_CHOICE:
        index = question.correct_option_index
        if index is not None and 0 <= index < len(question.options):
            return str(question.options[index])
        return ""
    return question.answer_text or ""


def _answer_should_create_flashcard(question: Question, answer: Answer) -> bool:
    """Wrong objective answers and partial/open-ended misses become cards."""
    if question.question_type in {QuestionType.MULTIPLE_CHOICE, QuestionType.FILL_BLANK}:
        return answer.is_correct is False
    if question.question_type == QuestionType.SHORT_ANSWER:
        return answer.score is not None and answer.score < 1
    return False


async def _create_wrong_answer_flashcard(
    db: AsyncSession, question: Question, answer: Answer
) -> None:
    """Create one elevated card for a wrong answer, idempotent by source answer."""
    existing = (
        await db.execute(
            select(Flashcard).where(Flashcard.source_answer_id == answer.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    correct_answer = _correct_answer_text(question)
    source_text = (question.source_span or {}).get("text") or ""
    back_parts = []
    if correct_answer:
        back_parts.append(f"正确答案：{correct_answer}")
    if source_text:
        back_parts.append(f"来源：{source_text}")
    if answer.feedback:
        back_parts.append(f"反馈：{answer.feedback}")

    db.add(
        Flashcard(
            document_id=question.document_id,
            concept_id=question.concept_id,
            source_answer_id=answer.id,
            source_question_id=question.id,
            front=question.stem,
            back="\n".join(back_parts) or question.explanation or question.stem,
            source_span=question.source_span,
            origin=FlashcardOrigin.WRONG_ANSWER,
            priority=FlashcardPriority.ELEVATED,
        )
    )


async def _remove_wrong_answer_flashcard(db: AsyncSession, answer: Answer) -> None:
    """Remove a stale wrong-answer card after the source answer is corrected."""
    existing = (
        await db.execute(
            select(Flashcard).where(
                Flashcard.source_answer_id == answer.id,
                Flashcard.origin == FlashcardOrigin.WRONG_ANSWER,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        await db.delete(existing)


@router.post("/{session_id}/answer", response_model=AnswerOut)
async def submit_answer(
    session_id: int,
    body: AnswerRequest,
    db: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm_client),
) -> AnswerOut:
    """提交单题作答：按题型判分/评分 + 生成反馈 + 落库 Answer，全部答完则结算会话。"""
    quiz = await db.get(QuizSession, session_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="答题会话不存在")
    if quiz.status == SessionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="答题会话已结束")
    if body.question_id not in (quiz.question_ids or []):
        raise HTTPException(status_code=400, detail="题目不属于该答题会话")

    question = await db.get(Question, body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")

    # 按题型分流判分/评分
    if question.question_type == QuestionType.SHORT_ANSWER:
        if not body.short_answer_text or not body.short_answer_text.strip():
            raise HTTPException(status_code=400, detail="简答题需提供作答文本")
        result = await score_short_answer(
            question, student_answer=body.short_answer_text, llm=llm
        )
        is_correct = None
        score = result.score
        feedback = result.feedback
        selected_option_index = None
        short_answer_text = body.short_answer_text
    elif question.question_type == QuestionType.FILL_BLANK:
        if not body.short_answer_text or not body.short_answer_text.strip():
            raise HTTPException(status_code=400, detail="填空题需提供作答文本")
        result = score_fill_blank(question, student_answer=body.short_answer_text)
        is_correct = result.is_correct
        score = None
        feedback = await generate_feedback(
            question,
            selected_option_index=-1,
            is_correct=is_correct,
            llm=llm,
        )
        selected_option_index = None
        short_answer_text = body.short_answer_text
    else:
        if body.selected_option_index is None:
            raise HTTPException(status_code=400, detail="选择题需提供所选选项下标")
        if not (0 <= body.selected_option_index < len(question.options)):
            raise HTTPException(status_code=422, detail="selected_option_index 超出选项范围")
        is_correct = body.selected_option_index == question.correct_option_index
        feedback = await generate_feedback(
            question,
            selected_option_index=body.selected_option_index,
            is_correct=is_correct,
            llm=llm,
        )
        score = None
        selected_option_index = body.selected_option_index
        short_answer_text = None

    # 幂等：同一会话+题目已有作答则更新，否则新建
    existing = (
        await db.execute(
            select(Answer).where(
                Answer.quiz_session_id == session_id,
                Answer.question_id == body.question_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        answer = Answer(
            quiz_session_id=session_id,
            question_id=body.question_id,
            selected_option_index=selected_option_index,
            is_correct=is_correct,
            short_answer_text=short_answer_text,
            score=score,
            feedback=feedback,
        )
        db.add(answer)
    else:
        existing.selected_option_index = selected_option_index
        existing.is_correct = is_correct
        existing.short_answer_text = short_answer_text
        existing.score = score
        existing.feedback = feedback
        answer = existing
    await db.flush()

    if _answer_should_create_flashcard(question, answer):
        await _create_wrong_answer_flashcard(db, question, answer)
    else:
        await _remove_wrong_answer_flashcard(db, answer)

    # 全部题目作答完毕 → 结算会话（选择题按 is_correct 计 1，简答题按 score 计分）
    rows = (
        await db.execute(
            select(Answer.question_id, Answer.is_correct, Answer.score).where(
                Answer.quiz_session_id == session_id
            )
        )
    ).all()
    answered_ids = {row[0] for row in rows}
    if answered_ids == set(quiz.question_ids or []):
        correct = sum(1 for row in rows if row[1]) + sum(
            row[2] for row in rows if row[2] is not None
        )
        total = len(quiz.question_ids) or 1
        quiz.status = SessionStatus.COMPLETED
        quiz.score = correct / total
        quiz.completed_at = datetime.now(timezone.utc)
        await db.flush()

    await db.commit()
    await db.refresh(answer)
    return AnswerOut.model_validate(answer)


__all__ = ["router"]
