"""答题路由：POST /api/quiz-sessions/{id}/answer —— 即时判分 + LLM 引用原文反馈。

切片 1.1：
- 选择题确定性判分（selected == correct），不依赖 LLM。
- LLM 据学生作答 + source_span 生成引用课件原文的反馈；空响应/异常走兜底。
- 同一会话+题目重答幂等（更新而非新增 Answer），便于改答案。
- 答完会话全部题目后置 status=completed + score=正确数/总数 + completed_at。

LLM 全程可 mock。answer 不在出题 router（prefix /api/documents）下，故独立成路由。
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_llm_client, get_session
from quizcraft.models.quiz import Answer, Question, QuizSession, SessionStatus
from quizcraft.schemas.quiz import AnswerOut, AnswerRequest
from quizcraft.services.llm import LLMClient
from quizcraft.services.quiz.feedback import generate_feedback

router = APIRouter(prefix="/api/quiz-sessions", tags=["quiz"])


@router.post("/{session_id}/answer", response_model=AnswerOut)
async def submit_answer(
    session_id: int,
    body: AnswerRequest,
    db: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm_client),
) -> AnswerOut:
    """提交单题作答：判分 + 生成反馈 + 落库 Answer，全部答完则结算会话。"""
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
    if not (0 <= body.selected_option_index < len(question.options)):
        raise HTTPException(status_code=422, detail="selected_option_index 超出选项范围")

    is_correct = body.selected_option_index == question.correct_option_index
    feedback = await generate_feedback(
        question,
        selected_option_index=body.selected_option_index,
        is_correct=is_correct,
        llm=llm,
    )

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
            selected_option_index=body.selected_option_index,
            is_correct=is_correct,
            feedback=feedback,
        )
        db.add(answer)
    else:
        existing.selected_option_index = body.selected_option_index
        existing.is_correct = is_correct
        existing.feedback = feedback
        answer = existing
    await db.flush()

    # 全部题目作答完毕 → 结算会话
    rows = (
        await db.execute(
            select(Answer.question_id, Answer.is_correct).where(
                Answer.quiz_session_id == session_id
            )
        )
    ).all()
    answered_ids = {row[0] for row in rows}
    if answered_ids == set(quiz.question_ids or []):
        correct = sum(1 for row in rows if row[1])
        total = len(quiz.question_ids) or 1
        quiz.status = SessionStatus.COMPLETED
        quiz.score = correct / total
        quiz.completed_at = datetime.now(timezone.utc)
        await db.flush()

    await db.commit()
    await db.refresh(answer)
    return AnswerOut.model_validate(answer)


__all__ = ["router"]
