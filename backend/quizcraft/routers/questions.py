"""题目管理路由（切片 1.2 子系统5 标记坏题）。

- POST /api/questions/{id}/flag：标记坏题（is_flagged=True），幂等
- DELETE /api/questions/{id}/flag：取消标记（is_flagged=False）

"移出 practice pool" 的可测行为在 GET /api/documents/{id}/questions（quiz router）：
已标记题不返回。标记不影响已生成的答题会话——Question 仍存于 DB，已包含它的 QuizSession
照常可答；仅新建查询的练习池列表排除坏题（前端据此隐藏/禁用，避免再练）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_session
from quizcraft.models.quiz import Question
from quizcraft.schemas.quiz import QuestionOut

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("/{question_id}/flag", response_model=QuestionOut)
async def flag_question(
    question_id: int,
    db: AsyncSession = Depends(get_session),
) -> QuestionOut:
    """标记坏题：is_flagged=True，使其移出练习池（GET 练习池列表不再返回）。"""
    q = await db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    q.is_flagged = True
    await db.commit()
    await db.refresh(q)
    return QuestionOut.model_validate(q)


@router.delete("/{question_id}/flag", response_model=QuestionOut)
async def unflag_question(
    question_id: int,
    db: AsyncSession = Depends(get_session),
) -> QuestionOut:
    """取消标记坏题：is_flagged=False，题重回练习池。"""
    q = await db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    q.is_flagged = False
    await db.commit()
    await db.refresh(q)
    return QuestionOut.model_validate(q)


__all__ = ["router"]
