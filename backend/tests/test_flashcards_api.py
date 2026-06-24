"""Flashcard API behavior tests for issue #20.

Public behavior: answering a question incorrectly creates a source-linked flashcard
that can be listed through the flashcard API. LLM calls are mocked through the app
dependency override.
"""
from quizcraft.models.document import Concept, Document, DocumentStatus, Section
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
