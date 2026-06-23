"""出题 API 测试：Mock LLM，验证 POST /api/documents/{id}/generate-quiz 端到端落库与响应。

绕过 PDF 上传：直接用 session fixture 插 Document+Section，聚焦出题 LLM 交互而非解析。
"""
from starlette.status import HTTP_201_CREATED

from quizcraft.models.document import Document, DocumentStatus, Section


async def _seed_document(session) -> int:
    """直接往 DB 插一份带分块的文档（出题测试聚焦 LLM，不走 PDF 解析）。"""
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
    await session.commit()
    return doc.id


STEP1 = (
    '{"concepts": [{"name": "光合作用", "description": "植物利用光能合成有机物", '
    '"bloom_level": "记忆", "source_text": "光合作用是植物利用光能合成有机物的过程。"}]}'
)
STEP2 = (
    '{"questions": [{"stem": "光反应发生在？", "options": ["细胞核", "类囊体膜", "细胞壁", "液泡"], '
    '"correct_option_index": 1, "explanation": "光反应在类囊体膜", "bloom_level": "记忆", '
    '"difficulty": "easy", "source_text": "光反应发生在类囊体膜上。"}]}'
)
EVAL_HIGH = '{"accuracy": 0.9, "source_grounding": 0.9}'


async def test_generate_quiz_creates_session_and_questions(session, client, llm_mock):
    """出题 → 201，落库 Concepts/Questions + 新建 QuizSession，响应含来源锚定字段。"""
    doc_id = await _seed_document(session)
    llm_mock.set_responses([STEP1, STEP2, EVAL_HIGH])

    resp = await client.post(f"/api/documents/{doc_id}/generate-quiz")

    assert resp.status_code == HTTP_201_CREATED, resp.text
    body = resp.json()

    qs = body["quiz_session"]
    assert qs["document_id"] == doc_id
    assert qs["status"] == "in_progress"
    assert qs["total"] == 1
    assert qs["question_ids"] == [body["questions"][0]["id"]]

    q = body["questions"][0]
    assert q["stem"] == "光反应发生在？"
    assert q["options"] == ["细胞核", "类囊体膜", "细胞壁", "液泡"]
    assert q["correct_option_index"] == 1
    assert q["source_span"]["page"] == 12
    assert q["source_span"]["section_path"] == "第2章 光合作用"
    assert q["source_span"]["text"] == "光反应发生在类囊体膜上。"
    assert q["self_eval_score"] == 0.9

    assert len(body["concepts"]) == 1
    assert body["concepts"][0]["name"] == "光合作用"
    assert body["concepts"][0]["source_span"]["page"] == 12


async def test_generate_quiz_404_unknown_document(client, llm_mock):
    """出题目标文档不存在 → 404。"""
    llm_mock.set_responses([])
    resp = await client.post("/api/documents/9999/generate-quiz")
    assert resp.status_code == 404


async def test_generate_quiz_400_when_no_sections(session, client, llm_mock):
    """文档无分块（无可出题内容）→ 400。"""
    doc = Document(filename="empty.pdf", page_count=0, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.commit()
    llm_mock.set_responses([])
    resp = await client.post(f"/api/documents/{doc.id}/generate-quiz")
    assert resp.status_code == 400


async def test_generated_question_correct_answer_persisted(session, client, llm_mock):
    """正确答案落库可回查（判分子系统将依赖此字段，验证未泄露到前端视图留待切片 1.4）。"""
    doc_id = await _seed_document(session)
    llm_mock.set_responses([STEP1, STEP2, EVAL_HIGH])

    resp = await client.post(f"/api/documents/{doc_id}/generate-quiz")
    assert resp.status_code == HTTP_201_CREATED
    question_id = resp.json()["questions"][0]["id"]

    # 回查 DB 确认正确答案与 source_span 落库
    from sqlalchemy import select

    from quizcraft.models.quiz import Question

    q = (
        await session.execute(select(Question).where(Question.id == question_id))
    ).scalar_one()
    assert q.correct_option_index == 1
    assert q.source_span["text"] == "光反应发生在类囊体膜上。"
