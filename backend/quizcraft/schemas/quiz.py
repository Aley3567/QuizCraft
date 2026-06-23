"""出题与答题相关 Pydantic 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from quizcraft.models.quiz import QuestionType, SessionStatus


class ConceptOut(BaseModel):
    """提取出的学习概念响应，携带 source_span 供溯源。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    source_span: dict  # {page, section_path, text}
    bloom_level: str | None


class QuestionOut(BaseModel):
    """题目响应：含正确答案与解析（用于出题后预览 / API 集成测试）。

    答题前端视图（不含正确答案，防止泄露）在切片 1.4 答题反馈子系统补；
    本 schema 服务于出题后预览与端到端集成测试。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    concept_id: int | None
    section_id: int | None
    question_type: QuestionType
    stem: str
    options: list
    correct_option_index: int
    explanation: str | None
    source_span: dict  # {page, section_path, text}
    bloom_level: str | None
    difficulty: str | None
    self_eval_score: float | None


class QuizSessionOut(BaseModel):
    """答题会话响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    question_ids: list
    status: SessionStatus
    score: float | None
    total: int | None
    created_at: datetime | None = None


class QuizGenerationResponse(BaseModel):
    """出题 API 响应：新建的答题会话 + 生成的题目 + 提取的概念。"""

    quiz_session: QuizSessionOut
    questions: list[QuestionOut]
    concepts: list[ConceptOut]


class AnswerRequest(BaseModel):
    """答题请求：指明作答的题目与所选选项下标。

    带 question_id（而非按会话顺序自动推进）使作答明确、可重答、可乱序，
    便于切片 1.2 的交叉混合出题与重答场景。
    """

    question_id: int
    selected_option_index: int


class AnswerOut(BaseModel):
    """答题响应：判分结果 + 引用原文的 LLM 反馈。

    不含 correct_option_index：前端通过 is_correct 与 feedback 文本理解对错，
    正确答案不直接以下标暴露（防泄露，对齐切片 1.4 答题视图设计）。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_session_id: int
    question_id: int
    selected_option_index: int | None
    is_correct: bool | None
    feedback: str | None
