"""Flashcard API behavior tests for issue #20.

Public behavior: answering a question incorrectly creates a source-linked flashcard
that can be listed through the flashcard API. LLM calls are mocked through the app
dependency override.
"""
import pytest
from sqlalchemy import select

from quizcraft.models.document import Concept, Document, DocumentStatus, Section
from quizcraft.models.flashcard import ReviewLog
from quizcraft.models.quiz import Question, QuestionType, QuizSession, SessionStatus


FEEDBACK = "你的课件第12页提到：光反应发生在类囊体膜上，所以选B。"


async def _seed_concept_question(session):
    doc = Document(filename="lecture.pdf", page_count=1, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()

    section = Section(
        document_id=doc.id,
        section_path="第2章 光合作用",
        page_number=12,
        content="光反应发生在类囊体膜上。",
        order_index=0,
        token_count=10,
    )
    session.add(section)
    await session.flush()

    concept = Concept(
        document_id=doc.id,
        section_id=section.id,
        name="光反应",
        description="光合作用中依赖光能的反应阶段",
        source_span={
            "page": 12,
            "section_path": "第2章 光合作用",
            "text": "光反应发生在类囊体膜上。",
        },
        bloom_level="理解",
    )
    session.add(concept)
    await session.flush()

    question = Question(
        document_id=doc.id,
        concept_id=concept.id,
        section_id=section.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        stem="光反应发生在哪里？",
        options=["细胞核", "类囊体膜", "细胞壁", "液泡"],
        correct_option_index=1,
        explanation="光反应在类囊体膜上进行。",
        source_span={
            "page": 12,
            "section_path": "第2章 光合作用",
            "text": "光反应发生在类囊体膜上。",
        },
        bloom_level="记忆",
        difficulty="easy",
        self_eval_score=0.9,
    )
    session.add(question)
    await session.flush()

    quiz = QuizSession(
        document_id=doc.id,
        question_ids=[question.id],
        status=SessionStatus.IN_PROGRESS,
        total=1,
    )
    session.add(quiz)
    await session.commit()
    return doc.id, concept.id, quiz.id, question.id


async def _seed_concepts(session, count: int):
    """Seed multiple source-linked concepts for public flashcard creation tests."""
    doc = Document(filename="lecture.pdf", page_count=1, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()

    section = Section(
        document_id=doc.id,
        section_path="第2章 光合作用",
        page_number=12,
        content="光反应、暗反应和叶绿体都与光合作用有关。",
        order_index=0,
        token_count=20,
    )
    session.add(section)
    await session.flush()

    concept_ids = []
    for index in range(count):
        concept = Concept(
            document_id=doc.id,
            section_id=section.id,
            name=f"概念{index + 1}",
            description=f"概念{index + 1}的定义",
            source_span={
                "page": 12,
                "section_path": "第2章 光合作用",
                "text": "光反应、暗反应和叶绿体都与光合作用有关。",
            },
            bloom_level="理解",
        )
        session.add(concept)
        await session.flush()
        concept_ids.append(concept.id)

    await session.commit()
    return doc.id, concept_ids


async def _seed_open_ended_flashcard_quiz(session, question_type: QuestionType):
    """Seed one target fill/short-answer question plus one unanswered blocker.

    Keeping a second question unanswered leaves the session open so the same
    public answer endpoint can exercise answer correction behavior.
    """
    doc = Document(filename="lecture.pdf", page_count=1, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()

    section = Section(
        document_id=doc.id,
        section_path="第2章 光合作用",
        page_number=12,
        content="光反应发生在类囊体膜上。",
        order_index=0,
        token_count=10,
    )
    session.add(section)
    await session.flush()

    concept = Concept(
        document_id=doc.id,
        section_id=section.id,
        name="光反应",
        description="光合作用中依赖光能的反应阶段",
        source_span={
            "page": 12,
            "section_path": "第2章 光合作用",
            "text": "光反应发生在类囊体膜上。",
        },
        bloom_level="理解",
    )
    session.add(concept)
    await session.flush()

    target = Question(
        document_id=doc.id,
        concept_id=concept.id,
        section_id=section.id,
        question_type=question_type,
        stem=(
            "光反应发生在____上。"
            if question_type == QuestionType.FILL_BLANK
            else "简述光反应的发生部位。"
        ),
        options=[],
        correct_option_index=None,
        answer_text=(
            "类囊体膜"
            if question_type == QuestionType.FILL_BLANK
            else "光反应发生在类囊体膜上。"
        ),
        explanation="考察光反应部位。",
        source_span={
            "page": 12,
            "section_path": "第2章 光合作用",
            "text": "光反应发生在类囊体膜上。",
        },
        bloom_level="理解",
        difficulty="medium",
        self_eval_score=None,
    )
    blocker = Question(
        document_id=doc.id,
        concept_id=concept.id,
        section_id=section.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        stem="保留会话未完成的题目",
        options=["A", "B", "C", "D"],
        correct_option_index=0,
        explanation="占位题。",
        source_span={
            "page": 12,
            "section_path": "第2章 光合作用",
            "text": "光反应发生在类囊体膜上。",
        },
        bloom_level="记忆",
        difficulty="easy",
        self_eval_score=0.9,
    )
    session.add_all([target, blocker])
    await session.flush()

    quiz = QuizSession(
        document_id=doc.id,
        question_ids=[target.id, blocker.id],
        status=SessionStatus.IN_PROGRESS,
        total=2,
    )
    session.add(quiz)
    await session.commit()
    return doc.id, concept.id, quiz.id, target.id


async def test_wrong_answer_creates_source_linked_flashcard(session, client, llm_mock):
    """Wrong MCQ answer -> GET /api/flashcards shows a high-priority card."""
    document_id, concept_id, quiz_id, question_id = await _seed_concept_question(session)
    llm_mock.set_responses([FEEDBACK])

    answer_resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": question_id, "selected_option_index": 0},
    )
    assert answer_resp.status_code == 200, answer_resp.text
    assert answer_resp.json()["is_correct"] is False

    list_resp = await client.get(f"/api/flashcards?document_id={document_id}")

    assert list_resp.status_code == 200, list_resp.text
    cards = list_resp.json()
    assert len(cards) == 1
    card = cards[0]
    assert card["document_id"] == document_id
    assert card["concept_id"] == concept_id
    assert card["source_answer_id"] is not None
    assert card["origin"] == "wrong_answer"
    assert card["priority"] == "elevated"
    assert card["front"] == "光反应发生在哪里？"
    assert "类囊体膜" in card["back"]
    assert card["source_span"] == {
        "page": 12,
        "section_path": "第2章 光合作用",
        "text": "光反应发生在类囊体膜上。",
    }

    filtered = await client.get(f"/api/flashcards?concept_id={concept_id}")
    assert filtered.status_code == 200, filtered.text
    assert [card["id"] for card in filtered.json()] == [card["id"]]


async def test_create_concept_flashcards_without_duplicates(session, client):
    """Concept card creation is idempotent and keeps source citation metadata."""
    document_id, concept_id, _quiz_id, _question_id = await _seed_concept_question(session)

    first_resp = await client.post(
        "/api/flashcards/from-concepts",
        json={"concept_ids": [concept_id]},
    )

    assert first_resp.status_code == 201, first_resp.text
    first_cards = first_resp.json()
    assert len(first_cards) == 1
    card = first_cards[0]
    assert card["document_id"] == document_id
    assert card["concept_id"] == concept_id
    assert card["source_answer_id"] is None
    assert card["source_question_id"] is None
    assert card["origin"] == "concept"
    assert card["priority"] == "normal"
    assert card["front"] == "什么是光反应？"
    assert "光合作用中依赖光能的反应阶段" in card["back"]
    assert card["source_span"] == {
        "page": 12,
        "section_path": "第2章 光合作用",
        "text": "光反应发生在类囊体膜上。",
    }

    second_resp = await client.post(
        "/api/flashcards/from-concepts",
        json={"concept_ids": [concept_id]},
    )

    assert second_resp.status_code == 201, second_resp.text
    assert [item["id"] for item in second_resp.json()] == [card["id"]]

    list_resp = await client.get(f"/api/flashcards?document_id={document_id}")
    assert list_resp.status_code == 200, list_resp.text
    assert [item["id"] for item in list_resp.json()] == [card["id"]]


async def test_reviewing_new_due_card_records_log_and_updates_schedule(session, client):
    """New card -> due list -> Good review records log and moves schedule forward."""
    document_id, concept_id, _quiz_id, _question_id = await _seed_concept_question(session)
    create_resp = await client.post(
        "/api/flashcards/from-concepts",
        json={"concept_ids": [concept_id]},
    )
    assert create_resp.status_code == 201, create_resp.text
    card = create_resp.json()[0]

    due_resp = await client.get("/api/flashcards/due")
    assert due_resp.status_code == 200, due_resp.text
    due_cards = due_resp.json()
    assert [item["id"] for item in due_cards] == [card["id"]]
    assert due_cards[0]["document_id"] == document_id
    assert due_cards[0]["state"] == "new"
    original_due = due_cards[0]["due_date"]

    review_resp = await client.post(
        f"/api/flashcards/{card['id']}/review",
        json={"rating": "good"},
    )

    assert review_resp.status_code == 200, review_resp.text
    reviewed = review_resp.json()
    assert reviewed["id"] == card["id"]
    assert reviewed["state"] == "review"
    assert reviewed["reps"] == 1
    assert reviewed["lapses"] == 0
    assert reviewed["last_review"] is not None
    assert reviewed["due_date"] != original_due
    assert reviewed["scheduled_days"] >= 1

    due_after_review = await client.get("/api/flashcards/due")
    assert due_after_review.status_code == 200, due_after_review.text
    assert due_after_review.json() == []

    logs = (await session.execute(select(ReviewLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].flashcard_id == card["id"]
    assert logs[0].rating == "good"
    assert logs[0].scheduled_days == reviewed["scheduled_days"]


@pytest.mark.parametrize(
    ("rating", "expected_state", "expected_lapses", "expected_scheduled_days", "remains_due"),
    [
        ("Again", "learning", 1, 0, True),
        ("Hard", "review", 0, 1, False),
        ("Easy", "review", 0, 4, False),
    ],
)
async def test_review_endpoint_accepts_all_remaining_ratings(
    session,
    client,
    rating,
    expected_state,
    expected_lapses,
    expected_scheduled_days,
    remains_due,
):
    """Again/Hard/Easy reviews update public schedule state and create review logs."""
    _document_id, concept_id, _quiz_id, _question_id = await _seed_concept_question(session)
    create_resp = await client.post(
        "/api/flashcards/from-concepts",
        json={"concept_ids": [concept_id]},
    )
    assert create_resp.status_code == 201, create_resp.text
    card = create_resp.json()[0]

    review_resp = await client.post(
        f"/api/flashcards/{card['id']}/review",
        json={"rating": rating},
    )

    assert review_resp.status_code == 200, review_resp.text
    reviewed = review_resp.json()
    assert reviewed["id"] == card["id"]
    assert reviewed["state"] == expected_state
    assert reviewed["reps"] == 1
    assert reviewed["lapses"] == expected_lapses
    assert reviewed["last_review"] is not None
    assert reviewed["scheduled_days"] == expected_scheduled_days

    due_after_review = await client.get("/api/flashcards/due")
    assert due_after_review.status_code == 200, due_after_review.text
    due_ids = [item["id"] for item in due_after_review.json()]
    if remains_due:
        assert due_ids == [card["id"]]
    else:
        assert due_ids == []

    logs = (await session.execute(select(ReviewLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].flashcard_id == card["id"]
    assert logs[0].rating == rating.lower()
    assert logs[0].scheduled_days == expected_scheduled_days


async def test_review_settings_daily_new_limit_reduces_due_cards(session, client):
    """Changing review settings constrains the public due-card query."""
    _document_id, concept_ids = await _seed_concepts(session, 3)
    create_resp = await client.post(
        "/api/flashcards/from-concepts",
        json={"concept_ids": concept_ids},
    )
    assert create_resp.status_code == 201, create_resp.text
    created_ids = [item["id"] for item in create_resp.json()]

    default_due_resp = await client.get("/api/flashcards/due")
    assert default_due_resp.status_code == 200, default_due_resp.text
    assert [item["id"] for item in default_due_resp.json()] == created_ids

    settings_resp = await client.put(
        "/api/settings/review",
        json={"daily_new_limit": 2, "daily_review_limit": 20, "desired_retention": 0.9},
    )
    assert settings_resp.status_code == 200, settings_resp.text
    assert settings_resp.json()["daily_new_limit"] == 2

    limited_due_resp = await client.get("/api/flashcards/due")
    assert limited_due_resp.status_code == 200, limited_due_resp.text
    assert [item["id"] for item in limited_due_resp.json()] == created_ids[:2]


@pytest.mark.parametrize(
    ("question_type", "wrong_text", "wrong_llm", "correct_text", "correct_llm"),
    [
        (QuestionType.FILL_BLANK, "细胞核", FEEDBACK, "类囊体膜", FEEDBACK),
        (
            QuestionType.SHORT_ANSWER,
            "在细胞核里",
            '{"score": 0.4, "feedback": "还没答到课件第12页的类囊体膜。"}',
            "光反应发生在类囊体膜上。",
            (
                '{"score": 1, "feedback": '
                '"答对了，课件第12页说明光反应发生在类囊体膜上。"}'
            ),
        ),
    ],
)
async def test_corrected_open_ended_answer_removes_wrong_answer_flashcard(
    session,
    client,
    llm_mock,
    question_type,
    wrong_text,
    wrong_llm,
    correct_text,
    correct_llm,
):
    """Correcting a fill/short-answer response removes its stale wrong-answer card."""
    document_id, concept_id, quiz_id, question_id = await _seed_open_ended_flashcard_quiz(
        session, question_type
    )
    llm_mock.set_responses([wrong_llm, correct_llm])

    wrong_resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": question_id, "short_answer_text": wrong_text},
    )
    assert wrong_resp.status_code == 200, wrong_resp.text

    wrong_cards_resp = await client.get(f"/api/flashcards?document_id={document_id}")
    assert wrong_cards_resp.status_code == 200, wrong_cards_resp.text
    wrong_cards = wrong_cards_resp.json()
    assert len(wrong_cards) == 1
    card = wrong_cards[0]
    assert card["concept_id"] == concept_id
    assert card["origin"] == "wrong_answer"
    assert card["priority"] == "elevated"
    assert card["source_question_id"] == question_id
    assert card["source_answer_id"] == wrong_resp.json()["id"]
    assert "类囊体膜" in card["back"]
    assert card["source_span"] == {
        "page": 12,
        "section_path": "第2章 光合作用",
        "text": "光反应发生在类囊体膜上。",
    }

    correct_resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": question_id, "short_answer_text": correct_text},
    )
    assert correct_resp.status_code == 200, correct_resp.text

    corrected_cards_resp = await client.get(f"/api/flashcards?document_id={document_id}")
    assert corrected_cards_resp.status_code == 200, corrected_cards_resp.text
    assert corrected_cards_resp.json() == []
