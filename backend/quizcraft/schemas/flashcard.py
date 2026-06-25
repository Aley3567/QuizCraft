"""Flashcard API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quizcraft.models.flashcard import FlashcardOrigin, FlashcardPriority, FlashcardRating


class FlashcardOut(BaseModel):
    """Public flashcard response for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    concept_id: int | None
    source_answer_id: int | None
    source_question_id: int | None
    front: str
    back: str
    source_span: dict
    origin: FlashcardOrigin
    priority: FlashcardPriority
    state: str
    stability: float
    difficulty: float
    due_date: datetime
    last_review: datetime | None
    reps: int
    lapses: int
    created_at: datetime | None = None


class ConceptFlashcardCreate(BaseModel):
    """Request to create source-linked cards from extracted concepts."""

    concept_ids: list[int] = Field(min_length=1)


class FlashcardReviewRequest(BaseModel):
    """Review rating from a flip-card session."""

    rating: FlashcardRating

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_rating(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value


class FlashcardUpdate(BaseModel):
    """Request payload for editing flashcard content."""

    front: str | None = None
    back: str | None = None


class FlashcardReviewOut(FlashcardOut):
    """Review response including this review's scheduled interval."""

    scheduled_days: int
