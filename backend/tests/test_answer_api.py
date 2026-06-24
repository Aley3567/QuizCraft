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


# ---------- 子系统3：简答题评分 API ----------

SA_FEEDBACK = '{"score": 0.8, "feedback": "你的课件第12页提到光反应发生在类囊体膜上。"}'


async def _seed_short_answer_quiz(session, *, n_questions: int = 1):
    """直接插一份带 N 道简答题的答题会话（简答评分测试聚焦 LLM rubric，不走出题 LLM）。"""
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
            question_type=QuestionType.SHORT_ANSWER,
            stem=f"简述光反应的发生部位（题{i}）",
            options=[],
            correct_option_index=None,
            answer_text="光反应发生在类囊体膜上，负责水的光解。",
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


async def _seed_mixed_quiz(session):
    """插一份混合答题会话：1 道选择题（正解下标0）+ 1 道简答题。"""
    quiz_id, mc_ids = await _seed_quiz(session, n_questions=1)  # 选择题正解下标0
    # 复用同一文档/会话不行（_seed_quiz 自建会话），改为独立构造混合会话
    doc = Document(filename="mixed.pdf", page_count=1, status=DocumentStatus.COMPLETE)
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

    mc = Question(
        document_id=doc.id,
        concept_id=None,
        section_id=section.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        stem="光反应发生在？",
        options=["细胞核", "类囊体膜", "细胞壁", "液泡"],
        correct_option_index=1,
        explanation="光反应在类囊体膜",
        source_span={"page": 12, "section_path": "第2章", "text": "光反应发生在类囊体膜上。"},
        bloom_level="记忆",
        difficulty="easy",
        self_eval_score=0.9,
    )
    sa = Question(
        document_id=doc.id,
        concept_id=None,
        section_id=section.id,
        question_type=QuestionType.SHORT_ANSWER,
        stem="简述光反应的发生部位",
        options=[],
        correct_option_index=None,
        answer_text="光反应发生在类囊体膜上。",
        explanation="考察光反应部位",
        source_span={"page": 12, "section_path": "第2章", "text": "光反应发生在类囊体膜上。"},
        bloom_level="理解",
        difficulty="medium",
        self_eval_score=None,
    )
    session.add_all([mc, sa])
    await session.flush()
    quiz = QuizSession(
        document_id=doc.id,
        question_ids=[mc.id, sa.id],
        status=SessionStatus.IN_PROGRESS,
        total=2,
    )
    session.add(quiz)
    await session.commit()
    return quiz.id, [mc.id, sa.id]


async def test_answer_short_answer_returns_score_and_feedback(session, client, llm_mock):
    """简答题提交作答文本 → 200，LLM rubric 评分 0-1 + 引用原文反馈，is_correct=None。"""
    quiz_id, qids = await _seed_short_answer_quiz(session, n_questions=1)
    llm_mock.set_responses([SA_FEEDBACK])

    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "short_answer_text": "在类囊体膜上"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score"] == 0.8
    assert body["is_correct"] is None
    assert body["short_answer_text"] == "在类囊体膜上"
    assert body["selected_option_index"] is None
    assert "类囊体膜" in body["feedback"]


async def test_answer_short_answer_falls_back_when_llm_empty(session, client, llm_mock):
    """简答 LLM 空响应 → 兜底 score=0 + 锚定页码的反馈（不 500，不阻塞作答）。"""
    quiz_id, qids = await _seed_short_answer_quiz(session, n_questions=1)
    llm_mock.set_responses([""])

    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "short_answer_text": "在细胞核里"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score"] == 0.0
    assert "12" in body["feedback"]  # 兜底锚定页码


async def test_answer_short_answer_missing_text_400(session, client, llm_mock):
    """简答题未提供作答文本 → 400。"""
    quiz_id, qids = await _seed_short_answer_quiz(session, n_questions=1)
    llm_mock.set_responses([])
    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0]},  # 无 short_answer_text
    )
    assert resp.status_code == 400


async def test_answer_short_answer_completes_session_with_score(session, client, llm_mock):
    """单道简答题答完 → 会话结算，score = 简答分数。"""
    quiz_id, qids = await _seed_short_answer_quiz(session, n_questions=1)
    llm_mock.set_responses([SA_FEEDBACK])

    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "short_answer_text": "在类囊体膜上"},
    )
    assert resp.status_code == 200, resp.text

    quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz_id))
    ).scalar_one()
    assert quiz.status == SessionStatus.COMPLETED
    assert quiz.score == 0.8


async def test_answer_mixed_session_completes_with_combined_score(session, client, llm_mock):
    """混合会话结算：选择题答对 +1，简答得分 +0.5，total=2 → score=0.75。"""
    quiz_id, qids = await _seed_mixed_quiz(session)
    llm_mock.set_responses([FEEDBACK, '{"score": 0.5, "feedback": "部分对，课件第12页"}'])

    # 选择题答对（选1=正解1）
    r1 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "selected_option_index": 1},
    )
    assert r1.status_code == 200, r1.text
    # 简答得分 0.5
    r2 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[1], "short_answer_text": "部分对"},
    )
    assert r2.status_code == 200, r2.text

    quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz_id))
    ).scalar_one()
    assert quiz.status == SessionStatus.COMPLETED
    assert quiz.score == 0.75  # (1 + 0.5) / 2


async def test_answer_short_answer_is_idempotent(session, client, llm_mock):
    """简答重答同一题 → 更新而非新增；最终评分以最后一次为准，会话以最终作答结算。"""
    quiz_id, qids = await _seed_short_answer_quiz(session, n_questions=2)
    llm_mock.set_responses(
        [
            '{"score": 0.3, "feedback": "差，课件第12页"}',  # q0 首答
            SA_FEEDBACK,  # q0 重答（0.8）
            '{"score": 0.5, "feedback": "部分对，课件第12页"}',  # q1 首答（结算）
        ]
    )

    r1 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "short_answer_text": "在细胞核"},
    )
    assert r1.json()["score"] == 0.3
    # 重答 q0（q1 未答，会话仍进行中）
    r2 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[0], "short_answer_text": "在类囊体膜上"},
    )
    assert r2.json()["score"] == 0.8
    # 答 q1 → 完成结算
    r3 = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qids[1], "short_answer_text": "部分对"},
    )
    assert r3.status_code == 200, r3.text

    answers = (
        await session.execute(select(Answer).where(Answer.quiz_session_id == quiz_id))
    ).scalars().all()
    assert len(answers) == 2  # 每题一条，无重复
    q0 = [a for a in answers if a.question_id == qids[0]]
    assert len(q0) == 1
    assert q0[0].score == 0.8  # 重答覆盖
    quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz_id))
    ).scalar_one()
    assert quiz.status == SessionStatus.COMPLETED
    assert quiz.score == 0.65  # (0.8 + 0.5) / 2
