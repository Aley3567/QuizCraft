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

    答题前端视图（不含正确答案/参考答案，防泄露）在切片 1.4 答题反馈子系统补；
    本 schema 服务于出题后预览与端到端集成测试（含 correct_option_index 与 answer_text）。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    concept_id: int | None
    section_id: int | None
    question_type: QuestionType
    stem: str
    options: list
    correct_option_index: int | None
    # 简答题参考答案/rubric（选择题为 None）；预览用，答题视图防泄露留子系统 4
    answer_text: str | None
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
    """答题请求：指明作答的题目与作答内容（按题型分流）。

    带 question_id（而非按会话顺序自动推进）使作答明确、可重答、可乱序，
    便于切片 1.2 的交叉混合出题与重答场景。
    - 选择题：传 selected_option_index（所选选项下标）
    - 简答题：传 short_answer_text（学生作答文本，LLM rubric 评分）
    """

    question_id: int
    selected_option_index: int | None = None
    short_answer_text: str | None = None


class AnswerOut(BaseModel):
    """答题响应：判分/评分结果 + 引用原文的 LLM 反馈。

    不含 correct_option_index：前端通过 is_correct/score 与 feedback 文本理解对错，
    正确答案不直接以下标暴露（防泄露，对齐切片 1.4 答题视图设计）。
    - 选择题：is_correct 确定性判分，score=None
    - 简答题：score 为 LLM rubric 评分 0-1，is_correct=None
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_session_id: int
    question_id: int
    selected_option_index: int | None
    short_answer_text: str | None
    is_correct: bool | None
    score: float | None
    feedback: str | None


class QuizGenerationRequest(BaseModel):
    """出题参数控制（切片 1.2 子系统 2）。

    所有字段可选，缺省时退回默认行为（与切片 1.1 无 body 调用兼容）：
    - number：目标题数，自评后截断保留高分题（None 不限）
    - difficulty_range：允许的难度集合（如 ["easy","medium"]），None=不限
    - question_types：题型集合，支持 multiple_choice / short_answer（判断/填空留后续配套评分）
    - chapter_scope：section_path 子串白名单，None=全部章节
    - bloom_distribution：Bloom 层级 → 比例，如 {"记忆": 0.4, "应用": 0.2, ...}
    - concepts_per_section / questions_per_concept：底层出题密度旋钮
    """

    number: int | None = None
    difficulty_range: list[str] | None = None
    question_types: list[str] | None = None
    chapter_scope: list[str] | None = None
    bloom_distribution: dict[str, float] | None = None
    concepts_per_section: int = 5
    questions_per_concept: int = 2
