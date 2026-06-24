"""Flashcard data model for cards generated from concepts and wrong answers."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from quizcraft.db import Base, TimestampMixin


class FlashcardOrigin(str, Enum):
    """Where a flashcard came from."""

    CONCEPT = "concept"
    WRONG_ANSWER = "wrong_answer"


class FlashcardPriority(str, Enum):
    """Priority marker used by later scheduling slices."""

    NORMAL = "normal"
    ELEVATED = "elevated"


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
