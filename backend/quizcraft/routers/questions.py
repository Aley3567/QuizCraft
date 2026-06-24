"""题目管理路由（切片 1.2 子系统5 标记坏题 + 子系统4 预览编辑/删除/确认进池）。

- PUT /api/questions/{id}：编辑题干/选项/正确答案/参考答案/解析（按题型校验）
- DELETE /api/questions/{id}：删除题（清理引用它的 QuizSession.question_ids，Answer 级联删）
- POST /api/questions/{id}/flag：标记坏题（is_flagged=True），幂等 —— 子系统5
- DELETE /api/questions/{id}/flag：取消标记（is_flagged=False）—— 子系统5
- POST /api/questions/{id}/publish：确认进练习池（in_practice_pool=True），幂等 —— 子系统4

"移出 practice pool" 的可测行为在 GET /api/documents/{id}/questions（quiz router）：
已标记题或草稿题不返回。标记/删除不影响已生成的答题会话——Question 仍存于 DB 时，
已包含它的 QuizSession 照常可答；删除时同步从引用它的 QuizSession.question_ids 移除
该 id，避免结算残留已删题。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_session
from quizcraft.models.quiz import Question, QuestionType, QuizSession
from quizcraft.schemas.quiz import QuestionOut, QuestionUpdateRequest

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.put("/{question_id}", response_model=QuestionOut)
async def update_question(
    question_id: int,
    body: QuestionUpdateRequest,
    db: AsyncSession = Depends(get_session),
) -> QuestionOut:
    """编辑题目：部分更新（None 字段保留原值），按题型校验编辑后合法性。

    - 选择题：options 非空 + correct_option_index 在范围内
    - 简答题：answer_text 非空白
    """
    q = await db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")

    if body.stem is not None:
        q.stem = body.stem
    if body.options is not None:
        q.options = body.options
    if body.correct_option_index is not None:
        q.correct_option_index = body.correct_option_index
    if body.answer_text is not None:
        q.answer_text = body.answer_text
    if body.explanation is not None:
        q.explanation = body.explanation

    if q.question_type == QuestionType.MULTIPLE_CHOICE:
        if not q.options:
            raise HTTPException(status_code=422, detail="选择题需提供选项")
        if q.correct_option_index is None or not (
            0 <= q.correct_option_index < len(q.options)
        ):
            raise HTTPException(
                status_code=422, detail="correct_option_index 超出选项范围"
            )
    else:  # SHORT_ANSWER
        if not q.answer_text or not q.answer_text.strip():
            raise HTTPException(status_code=422, detail="简答题需提供参考答案")

    await db.commit()
    await db.refresh(q)
    return QuestionOut.model_validate(q)


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_session),
) -> Response:
    """删除题目：从 DB 移除，并清理引用它的 QuizSession.question_ids。

    Answer 表对 question_id 有 ondelete=CASCADE，删题会级联删除其作答记录；
    QuizSession.question_ids 是 JSON 列表（非外键），需手动从中移除该 id，
    否则进行中的会话结算时 set(quiz.question_ids) 会残留已删题 id 永不可答。
    """
    q = await db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")

    result = await db.execute(
        select(QuizSession).where(QuizSession.document_id == q.document_id)
    )
    for quiz in result.scalars():
        if question_id in (quiz.question_ids or []):
            quiz.question_ids = [
                i for i in (quiz.question_ids or []) if i != question_id
            ]

    await db.delete(q)
    await db.commit()
    return Response(status_code=204)


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


@router.post("/{question_id}/publish", response_model=QuestionOut)
async def publish_question(
    question_id: int,
    db: AsyncSession = Depends(get_session),
) -> QuestionOut:
    """确认进练习池：in_practice_pool=True（草稿→已确认），幂等。"""
    q = await db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    q.in_practice_pool = True
    await db.commit()
    await db.refresh(q)
    return QuestionOut.model_validate(q)


__all__ = ["router"]
