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
