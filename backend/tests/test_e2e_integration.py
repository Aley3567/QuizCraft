"""切片 1.1 子系统 6：端到端集成测试。

一条用例串起「上传 PDF → 出题 → 答题 → 反馈」全链路（LLM mock，SQLite 内存，ASGITransport），
验证 source_span 从真实 PDF 解析贯穿到用户可见反馈——这是 QuizCraft 错题溯源差异化的数据基础。

与 test_documents_api / test_quiz_api / test_answer_api 的区别：
- 后三者各自绕过上下游（直接 seed DB）聚焦单子系统；
- 本文件**不绕过任何环节**，从真实生成 PDF 上传走完整链路，page/section_path 由解析动态决定而非硬编码。
"""
from sqlalchemy import select
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from _pdf_helper import make_pdf_bytes

from quizcraft.models.quiz import Answer, Question, QuizSession, SessionStatus

# 出题三段 mock（1 section → 1 concept → 1 question，自评高分保留）
STEP1 = (
    '{"concepts": [{"name": "光合作用", "description": "植物利用光能合成有机物", '
    '"bloom_level": "记忆", "source_text": "光合作用是植物利用光能合成有机物的过程。"}]}'
)
STEP2 = (
    '{"questions": [{"stem": "光反应发生在哪个结构？", "options": ["细胞核", "类囊体膜", "细胞壁", "液泡"], '
    '"correct_option_index": 1, "explanation": "光反应在类囊体膜上进行", "bloom_level": "记忆", '
    '"difficulty": "easy", "source_text": "光反应发生在类囊体膜上。"}]}'
)
EVAL_HIGH = '{"accuracy": 0.9, "source_grounding": 0.9}'
STEP2_SOURCE_TEXT = "光反应发生在类囊体膜上。"

# 答题反馈 mock（纯文本，不含硬编码页码——页码由真实解析决定）
FEEDBACK = "正确。光反应发生在类囊体膜上，所以该题选「类囊体膜」。"


def _lecture_pdf() -> bytes:
    """两页中文课件 PDF（与 test_documents_api 同款，确保能解析出带 page/section_path 的分块）。"""
    return make_pdf_bytes(
        [
            [(80, "第2章 光合作用", 18), (140, "光合作用是植物利用光能合成有机物的过程。", 11)],
            [(80, "光反应发生在类囊体膜上，暗反应在基质中。", 11)],
        ]
    )


async def _upload_and_generate(client, llm_mock):
    """全链路前半段：上传 PDF → 出题，返回 (doc_id, section0, quiz_session, question)。"""
    upload = await client.post(
        "/api/documents",
        files={"file": ("lecture.pdf", _lecture_pdf(), "application/pdf")},
    )
    assert upload.status_code == HTTP_201_CREATED, upload.text
    doc = upload.json()
    section0 = doc["sections"][0]

    llm_mock.set_responses([STEP1, STEP2, EVAL_HIGH])
    gen = await client.post(f"/api/documents/{doc['id']}/generate-quiz")
    assert gen.status_code == HTTP_201_CREATED, gen.text
    body = gen.json()
    return doc["id"], section0, body["quiz_session"], body["questions"][0]


async def test_e2e_upload_to_feedback_happy_path(session, client, llm_mock):
    """全链路：上传 PDF → 出题 → 答对 → LLM 反馈 → 会话结算。

    断言 source_span 从真实解析的 section 动态贯穿到 Concept / Question / 反馈 prompt，
    并验证答题落库与会话结算（score=1.0，status=completed）。
    """
    _doc_id, section0, quiz_session, question = await _upload_and_generate(client, llm_mock)
    page0 = section0["page_number"]
    path0 = section0["section_path"]

    # 出题响应：source_span 的 page/section_path 来自真实解析的 section（动态，非硬编码）
    assert question["source_span"]["page"] == page0
    assert question["source_span"]["section_path"] == path0
    assert question["source_span"]["text"] == STEP2_SOURCE_TEXT  # text 来自 LLM source_text

    quiz_id = quiz_session["id"]
    qid = question["id"]
    correct_idx = question["correct_option_index"]

    # 答对（选正确答案下标）
    llm_mock.set_responses([FEEDBACK])
    resp = await client.post(
        f"/api/quiz-sessions/{quiz_id}/answer",
        json={"question_id": qid, "selected_option_index": correct_idx},
    )
    assert resp.status_code == HTTP_200_OK, resp.text
    body = resp.json()
    assert body["is_correct"] is True
    assert body["feedback"] == FEEDBACK

    # source_span 注入了反馈 prompt（反馈调用是最后一条 LLM 调用）
    feedback_msgs = "".join(m.content for m in llm_mock.calls[-1])
    assert f"课件页码：{page0}" in feedback_msgs
    assert path0 in feedback_msgs
    assert STEP2_SOURCE_TEXT in feedback_msgs

    # 单题会话答完即结算
    assert quiz_session["total"] == 1
    db_quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz_id))
    ).scalar_one()
    assert db_quiz.status == SessionStatus.COMPLETED
    assert db_quiz.score == 1.0
    assert db_quiz.completed_at is not None

    # Answer 落库回查：反馈与判分一致
    answers = (
        await session.execute(select(Answer).where(Answer.quiz_session_id == quiz_id))
    ).scalars().all()
    assert len(answers) == 1
    assert answers[0].is_correct is True
    assert answers[0].feedback == FEEDBACK

    # Question 落库回查：source_span 锚定真实页码
    db_q = (
        await session.execute(select(Question).where(Question.id == qid))
    ).scalar_one()
    assert db_q.source_span["page"] == page0
    assert db_q.source_span["text"] == STEP2_SOURCE_TEXT


async def test_e2e_fallback_feedback_carries_real_source_span(session, client, llm_mock):
    """LLM 空响应 → 兜底反馈仍携带真实解析的页码/章节/原文。

    证明 source_span 确定性贯穿到用户可见反馈——即使 LLM 抖动，错题溯源不丢。
    """
    _doc_id, section0, _quiz_session, question = await _upload_and_generate(client, llm_mock)
    page0 = section0["page_number"]
    path0 = section0["section_path"]

    llm_mock.set_responses([""])  # LLM 空响应 → 走兜底
    resp = await client.post(
        f"/api/quiz-sessions/{_quiz_session['id']}/answer",
        json={
            "question_id": question["id"],
            "selected_option_index": question["correct_option_index"],
        },
    )
    assert resp.status_code == HTTP_200_OK, resp.text
    feedback = resp.json()["feedback"]

    # 兜底反馈锚定真实解析的页码、章节路径、LLM 给出的原文片段
    assert f"第{page0}页" in feedback
    assert path0 in feedback
    assert STEP2_SOURCE_TEXT in feedback
    assert resp.json()["is_correct"] is True  # 判分不依赖 LLM
