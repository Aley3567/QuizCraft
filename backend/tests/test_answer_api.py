"""答题 API 测试：Mock LLM，验证 POST /api/quiz-sessions/{id}/answer 端到端判分 + 反馈 + 会话结算。

绕过出题：直接用 session fixture 插 Document+Section+Question+QuizSession，聚焦答题判分与 LLM 反馈。
"""
from sqlalchemy import select

from quizcraft.models.document import Document, DocumentStatus, Section
from quizcraft.models.quiz import (
    Answer,
    Question,
    QuestionType,
    QuizSession,
    SessionStatus,
)

FEEDBACK = "你的课件第12页提到：光反应发生在类囊体膜上，所以选B。"


async def _seed_quiz(session, *, n_questions: int = 2):
    """直接插一份带 N 道选择题的答题会话（答题测试聚焦判分，不走出题 LLM）。

    correct_option_index = i % 4：题0 正解下标0，题1 正解下标1，便于构造对/错场景。
    """
    doc = Document(filename="lecture.pdf", page_count=1, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()
    section = Section(
        document_id=doc.id,
        section_path="第2章 光合作用",
        page_number=12,
        content="光合作用是植物利用光能合成有机物的过程。光反应发生在类囊体膜上。",
        order_index=0,
        token_count=20,
    )
    session.add(section)
    await session.flush()

    question_ids: list[int] = []
    for i in range(n_questions):
        q = Question(
            document_id=doc.id,
            concept_id=None,
            section_id=section.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            stem=f"题目{i}",
            options=["A", "B", "C", "D"],
            correct_option_index=i % 4,
            explanation="解析",
            source_span={
                "page": 12,
                "section_path": "第2章 光合作用",
                "text": "光反应发生在类囊体膜上。",
            },
            bloom_level="记忆",
            difficulty="easy",
            self_eval_score=0.9,
        )
        session.add(q)
        await session.flush()
        question_ids.append(q.id)

    quiz = QuizSession(
        document_id=doc.id,
        question_ids=question_ids,
        status=SessionStatus.IN_PROGRESS,
        total=len(question_ids),
    )
    session.add(quiz)
    await session.commit()
    return quiz.id, question_ids


async def test_answer_correct_returns_feedback_and_keeps_in_progress(session, client, llm_mock):
    """答对单题 → 200，is_correct=True，feedback 来自 LLM，会话仍进行中（未答完）。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=2)
    llm_mock.set_responses([FEEDBACK])

    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 0},  # 题0 正解下标0
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_correct"] is True
    assert body["feedback"] == FEEDBACK
    assert body["question_id"] == qids[0]
    assert body["selected_option_index"] == 0

    quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz_id))
    ).scalar_one()
    assert quiz.status == SessionStatus.IN_PROGRESS  # 还有一题未答
    assert quiz.score is None


async def test_answer_wrong_marks_incorrect_with_source_feedback(session, client, llm_mock):
    """答错 → is_correct=False，feedback 仍生成（引用原文）。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=1)
    llm_mock.set_responses([FEEDBACK])

    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 2},  # 题0 正解下标0，选2=错
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["is_correct"] is False
    assert resp.json()["feedback"] == FEEDBACK


async def test_answer_all_marks_session_completed_with_score(session, client, llm_mock):
    """答完全部题 → status=completed，score=正确数/总数，completed_at 非空。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=2)
    llm_mock.set_responses([FEEDBACK, FEEDBACK])

    # 题0 答对（选0=正解0），题1 答错（选0≠正解1）→ 1/2
    await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 0},
    )
    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[1], "selected_option_index": 0},
    )
    assert resp.status_code == 200, resp.text

    quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz_id))
    ).scalar_one()
    assert quiz.status == SessionStatus.COMPLETED
    assert quiz.score == 0.5
    assert quiz.completed_at is not None


async def test_answer_same_question_is_idempotent(session, client, llm_mock):
    """未答完前重答同一题 → 更新而非新增；重答结果参与最终结算。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=2)
    llm_mock.set_responses([FEEDBACK, FEEDBACK, FEEDBACK])

    # 先答错 qids[0]（会话仍进行中，qids[1] 未答）
    r1 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 2},
    )
    assert r1.json()["is_correct"] is False
    # 重答 qids[0] 改正（幂等覆盖，会话仍未答完）
    r2 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 0},
    )
    assert r2.json()["is_correct"] is True

    # qids[0] 仅一条 Answer，最终正确
    answers = (
        await session.execute(select(Answer).where(Answer.quiz_session_id == quiz_id))
    ).scalars().all()
    q0 = [a for a in answers if a.question_id == qids[0]]
    assert len(q0) == 1
    assert q0[0].is_correct is True

    # 答 qids[1]（选0，正解下标1，错）→ 完成，1/2 = 0.5
    r3 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[1], "selected_option_index": 0},
    )
    assert r3.status_code == 200, r3.text
    quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz_id))
    ).scalar_one()
    assert quiz.status == SessionStatus.COMPLETED
    assert quiz.score == 0.5

    answers_final = (
        await session.execute(select(Answer).where(Answer.quiz_session_id == quiz_id))
    ).scalars().all()
    assert len(answers_final) == 2  # 每题一条，无重复


async def test_answer_falls_back_when_llm_empty(session, client, llm_mock):
    """LLM 空响应 → feedback 走兜底，仍含页码来源。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=1)
    llm_mock.set_responses([""])

    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 0},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_correct"] is True
    assert "12" in body["feedback"]  # 兜底锚定页码


async def test_answer_404_unknown_session(client, llm_mock):
    """答题会话不存在 → 404。"""
    llm_mock.set_responses([FEEDBACK])
    resp = await client.post(
        "/api/quiz-sessions/9999/answer",
        json={"question_id": 1, "selected_option_index": 0},
    )
    assert resp.status_code == 404


async def test_answer_400_when_session_completed(session, client, llm_mock):
    """会话已结束再答 → 400。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=1)
    llm_mock.set_responses([FEEDBACK, FEEDBACK])
    # 答完 → completed
    await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 0},
    )
    # 再答 → 400
    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 0},
    )
    assert resp.status_code == 400


async def test_answer_400_question_not_in_session(session, client, llm_mock):
    """题目不属于该会话 → 400。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=1)
    llm_mock.set_responses([FEEDBACK])
    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0] + 9999, "selected_option_index": 0},
    )
    assert resp.status_code == 400


async def test_answer_422_selected_out_of_range(session, client, llm_mock):
    """selected_option_index 超出选项范围 → 422。"""
    quiz_id, qids = await _seed_quiz(session, n_questions=1)
    llm_mock.set_responses([FEEDBACK])
    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 5},  # options 只有 4 项
    )
    assert resp.status_code == 422
