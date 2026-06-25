"""Flashcard API routes."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_session
from quizcraft.models.document import Concept
from quizcraft.models.flashcard import (
    Flashcard,
    FlashcardOrigin,
    FlashcardPriority,
    FlashcardRating,
    ReviewLog,
    utcnow_naive,
)
from quizcraft.schemas.flashcard import (
    ConceptFlashcardCreate,
    FlashcardOut,
    FlashcardReviewOut,
    FlashcardReviewRequest,
    FlashcardUpdate,
)
from quizcraft.services.settings import load_review_settings

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


def _schedule_review(card: Flashcard, rating: FlashcardRating, now: datetime) -> int:
    """Small deterministic FSRS-style scheduler for the public review behavior."""
    if rating == FlashcardRating.AGAIN:
        card.state = "relearning" if card.reps else "learning"
        card.lapses += 1
        card.stability = max(0.1, card.stability * 0.5)
        card.difficulty = min(10.0, card.difficulty + 1.0)
        scheduled_days = 0
    elif rating == FlashcardRating.HARD:
        card.state = "review"
        card.stability = max(1.0, card.stability + 0.5)
        card.difficulty = min(10.0, card.difficulty + 0.4)
        scheduled_days = 1
    elif rating == FlashcardRating.GOOD:
        card.state = "review"
        card.stability = max(2.5, card.stability + 1.5)
        card.difficulty = max(1.0, card.difficulty - 0.2)
        scheduled_days = 1 if card.reps == 0 else max(2, round(card.stability))
    else:
        card.state = "review"
        card.stability = max(4.0, card.stability + 3.0)
        card.difficulty = max(1.0, card.difficulty - 0.6)
        scheduled_days = 4 if card.reps == 0 else max(4, round(card.stability * 1.5))

    card.reps += 1
    card.last_review = now
    card.due_date = now + timedelta(days=scheduled_days)
    return scheduled_days


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


@router.get("/due", response_model=list[FlashcardOut])
async def list_due_flashcards(
    session: AsyncSession = Depends(get_session),
) -> list[FlashcardOut]:
    """List new cards and review cards due now."""
    now = utcnow_naive()
    settings = await load_review_settings(session)
    result = await session.execute(
        select(Flashcard)
        .where(Flashcard.due_date <= now)
        .order_by(Flashcard.due_date, Flashcard.id)
    )
    new_cards = []
    review_cards = []
    for card in result.scalars().all():
        if card.state == "new":
            new_cards.append(card)
        else:
            review_cards.append(card)

    limited_cards = (
        new_cards[: settings.daily_new_limit]
        + review_cards[: settings.daily_review_limit]
    )
    limited_cards.sort(key=lambda card: (card.due_date, card.id))
    return [FlashcardOut.model_validate(card) for card in limited_cards]


@router.post("/{flashcard_id}/review", response_model=FlashcardReviewOut)
async def review_flashcard(
    flashcard_id: int,
    body: FlashcardReviewRequest,
    session: AsyncSession = Depends(get_session),
) -> FlashcardReviewOut:
    """Rate a due flashcard and record the scheduling event."""
    card = await session.get(Flashcard, flashcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail="闪卡不存在")

    now = utcnow_naive()
    previous_last_review = card.last_review
    elapsed_days = 0
    if previous_last_review is not None:
        elapsed_days = max(0, (now.date() - previous_last_review.date()).days)

    scheduled_days = _schedule_review(card, body.rating, now)
    session.add(
        ReviewLog(
            flashcard_id=card.id,
            rating=body.rating.value,
            reviewed_at=now,
            elapsed_days=elapsed_days,
            scheduled_days=scheduled_days,
            stability=card.stability,
            difficulty=card.difficulty,
        )
    )
    await session.commit()

    payload = FlashcardOut.model_validate(card).model_dump()
    payload["scheduled_days"] = scheduled_days
    return FlashcardReviewOut.model_validate(payload)


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


@router.put("/{flashcard_id}", response_model=FlashcardOut)
async def update_flashcard(
    flashcard_id: int,
    body: FlashcardUpdate,
    session: AsyncSession = Depends(get_session),
) -> FlashcardOut:
    """Update flashcard content fields used by management workflows."""
    card = await session.get(Flashcard, flashcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail="闪卡不存在")
    if body.front is None and body.back is None:
        raise HTTPException(status_code=400, detail="front/back 至少更新一项")

    if body.front is not None:
        card.front = body.front
    if body.back is not None:
        card.back = body.back

    await session.commit()
    return FlashcardOut.model_validate(card)


__all__ = ["router"]
