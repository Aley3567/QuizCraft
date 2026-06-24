"""Flashcard API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_session
from quizcraft.models.flashcard import Flashcard
from quizcraft.schemas.flashcard import FlashcardOut

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


@router.get("", response_model=list[FlashcardOut])
async def list_flashcards(
    document_id: int | None = None,
    concept_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[FlashcardOut]:
    """List flashcards, optionally scoped by document or concept."""
    stmt = select(Flashcard).order_by(Flashcard.id)
    if document_id is not None:
        stmt = stmt.where(Flashcard.document_id == document_id)
    if concept_id is not None:
        stmt = stmt.where(Flashcard.concept_id == concept_id)
    result = await session.execute(stmt)
    return [FlashcardOut.model_validate(card) for card in result.scalars().all()]


__all__ = ["router"]
