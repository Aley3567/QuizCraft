"""Flashcard data model for cards generated from concepts and wrong answers."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, Float, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from quizcraft.db import Base, TimestampMixin


def utcnow_naive() -> datetime:
    """Return UTC as a naive datetime for SQLite DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class FlashcardOrigin(str, Enum):
    """Where a flashcard came from."""

    CONCEPT = "concept"
    WRONG_ANSWER = "wrong_answer"


class FlashcardPriority(str, Enum):
    """Priority marker used by later scheduling slices."""

    NORMAL = "normal"
    ELEVATED = "elevated"


class FlashcardRating(str, Enum):
    """User review rating accepted by the review endpoint."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


class Flashcard(TimestampMixin, Base):
    """Source-linked flashcard, optionally generated from a wrong answer."""

    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[int | None] = mapped_column(
        ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_answer_id: Mapped[int | None] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"), nullable=True, unique=True, index=True
    )
    source_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    source_span: Mapped[dict] = mapped_column(JSON)
    origin: Mapped[FlashcardOrigin] = mapped_column(
        SAEnum(FlashcardOrigin), default=FlashcardOrigin.CONCEPT, nullable=False, index=True
    )
    priority: Mapped[FlashcardPriority] = mapped_column(
        SAEnum(FlashcardPriority), default=FlashcardPriority.NORMAL, nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    stability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    last_review: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ReviewLog(TimestampMixin, Base):
    """One public review action for a flashcard."""

    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    flashcard_id: Mapped[int] = mapped_column(
        ForeignKey("flashcards.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    elapsed_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scheduled_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stability: Mapped[float] = mapped_column(Float, nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False)
