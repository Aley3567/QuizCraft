"""Flashcard API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from quizcraft.models.flashcard import FlashcardOrigin, FlashcardPriority


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
    created_at: datetime | None = None
