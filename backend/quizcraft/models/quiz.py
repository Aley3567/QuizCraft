"""出题与答题数据模型：Question、QuizSession、Answer。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from quizcraft.db import Base, TimestampMixin


class QuestionType(str, Enum):
    """切片 1.1 只做选择题；判断题/填空题/简答题在切片 1.2 补。"""

    MULTIPLE_CHOICE = "multiple_choice"


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Question(TimestampMixin, Base):
    """两步生成法 Step 2 产物：带 source_span 的选择题。"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[int | None] = mapped_column(
        ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )

    question_type: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType), default=QuestionType.MULTIPLE_CHOICE, nullable=False
    )
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)  # ["选项A", "选项B", ...]
    correct_option_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_span: Mapped[dict] = mapped_column(JSON)  # {page, section_path, text}
    bloom_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 简化自评分数（accuracy + source-grounding 两维度，完整 6 维度延后到切片 1.2）
    self_eval_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class QuizSession(TimestampMixin, Base):
    """一次答题会话，记录包含的题目与得分。"""

    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    question_ids: Mapped[list] = mapped_column(JSON)  # 本次会话题目 id 列表
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus), default=SessionStatus.IN_PROGRESS, nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Answer(TimestampMixin, Base):
    """单题作答记录：选择题选项 + 判分 + LLM 引用原文反馈。"""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_session_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_sessions.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    selected_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
