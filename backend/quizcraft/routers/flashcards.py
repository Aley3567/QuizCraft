"""Flashcard API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_session
from quizcraft.models.document import Concept
from quizcraft.models.flashcard import Flashcard, FlashcardOrigin, FlashcardPriority
from quizcraft.schemas.flashcard import ConceptFlashcardCreate, FlashcardOut

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


def _dedupe_preserve_order(ids: list[int]) -> list[int]:
    """Keep request order while preventing duplicate cards from duplicate ids."""
    seen = set()
    ordered = []
    for item_id in ids:
        if item_id not in seen:
            seen.add(item_id)
            ordered.append(item_id)
    return ordered


def _concept_front(concept: Concept) -> str:
    return f"什么是{concept.name}？"


def _concept_back(concept: Concept) -> str:
    parts = []
    if concept.description:
        parts.append(concept.description)
    source_text = (concept.source_span or {}).get("text")
    if source_text:
        parts.append(f"来源：{source_text}")
    return "\n".join(parts) or concept.name


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


@router.post(
    "/from-concepts",
    response_model=list[FlashcardOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_flashcards_from_concepts(
    body: ConceptFlashcardCreate,
    session: AsyncSession = Depends(get_session),
) -> list[FlashcardOut]:
    """Create one normal-priority flashcard per concept, idempotently."""
    concept_ids = _dedupe_preserve_order(body.concept_ids)

    concepts = (
        await session.execute(select(Concept).where(Concept.id.in_(concept_ids)))
    ).scalars().all()
    concepts_by_id = {concept.id: concept for concept in concepts}
    missing = [concept_id for concept_id in concept_ids if concept_id not in concepts_by_id]
    if missing:
        raise HTTPException(status_code=404, detail=f"概念不存在: {missing[0]}")

    existing_cards = (
        await session.execute(
            select(Flashcard).where(
                Flashcard.origin == FlashcardOrigin.CONCEPT,
                Flashcard.concept_id.in_(concept_ids),
            )
        )
    ).scalars().all()
    cards_by_concept_id = {card.concept_id: card for card in existing_cards}

    for concept_id in concept_ids:
        if concept_id in cards_by_concept_id:
            continue
        concept = concepts_by_id[concept_id]
        card = Flashcard(
            document_id=concept.document_id,
            concept_id=concept.id,
            source_answer_id=None,
            source_question_id=None,
            front=_concept_front(concept),
            back=_concept_back(concept),
            source_span=concept.source_span,
            origin=FlashcardOrigin.CONCEPT,
            priority=FlashcardPriority.NORMAL,
        )
        session.add(card)
        cards_by_concept_id[concept_id] = card

    await session.commit()
    return [FlashcardOut.model_validate(cards_by_concept_id[item_id]) for item_id in concept_ids]


__all__ = ["router"]
