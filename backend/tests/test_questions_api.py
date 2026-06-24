"""题目管理 API 测试（切片 1.2 子系统5 标记坏题 + practice pool）。

- POST /api/questions/{id}/flag：标记坏题（is_flagged=True），幂等
- DELETE /api/questions/{id}/flag：取消标记（is_flagged=False）
- GET /api/documents/{id}/questions：练习池列表，排除 is_flagged=True（移出 practice pool）

绕过出题：直接 ORM 插 Document+Section+Question，聚焦标记与练习池可见性，不依赖 LLM。
"""
from sqlalchemy import select

from quizcraft.models.document import Document, DocumentStatus, Section
from quizcraft.models.quiz import Question, QuestionType


async def _seed_questions(session, n: int = 3):
    """直接插 N 道选择题（不同 stem），返回 (document_id, question_ids)。"""
    doc = Document(filename="lecture.pdf", page_count=1, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()
    section = Section(
        document_id=doc.id,
        section_path="第2章 光合作用",
        page_number=12,
        content="光合作用内容",
        order_index=0,
        token_count=10,
    )
    session.add(section)
    await session.flush()
    ids: list[int] = []
    for i in range(n):
        q = Question(
            document_id=doc.id,
            concept_id=None,
            section_id=section.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            stem=f"题目{i}",
            options=["A", "B", "C", "D"],
            correct_option_index=0,
            explanation="解析",
            source_span={"page": 12, "section_path": "第2章", "text": "光合作用内容"},
            bloom_level="记忆",
            difficulty="easy",
        )
        session.add(q)
        await session.flush()
        ids.append(q.id)
    await session.commit()
    return doc.id, ids


async def test_flag_question_marks_and_persists(session, client):
    """POST flag → is_flagged=True 落库，响应暴露 is_flagged，不影响其他题。"""
    _, qids = await _seed_questions(session, n=2)
    resp = await client.post(f"/api/questions/{qids[0]}/flag")
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_flagged"] is True

    q0 = (
        await session.execute(select(Question).where(Question.id == qids[0]))
    ).scalar_one()
    assert q0.is_flagged is True
    q1 = (
        await session.execute(select(Question).where(Question.id == qids[1]))
    ).scalar_one()
    assert q1.is_flagged is False


async def test_flag_question_idempotent(session, client):
    """重复 flag 同一题 → 仍 200，is_flagged 保持 True。"""
    _, qids = await _seed_questions(session, n=1)
    r1 = await client.post(f"/api/questions/{qids[0]}/flag")
    r2 = await client.post(f"/api/questions/{qids[0]}/flag")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["is_flagged"] is True
    assert r2.json()["is_flagged"] is True


async def test_unflag_question(session, client):
    """DELETE flag → 取消标记，is_flagged=False。"""
    _, qids = await _seed_questions(session, n=1)
    await client.post(f"/api/questions/{qids[0]}/flag")
    resp = await client.delete(f"/api/questions/{qids[0]}/flag")
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_flagged"] is False
    q = (
        await session.execute(select(Question).where(Question.id == qids[0]))
    ).scalar_one()
    assert q.is_flagged is False


async def test_flag_unknown_question_404(client):
    """标记不存在的题 → 404。"""
    resp = await client.post("/api/questions/9999/flag")
    assert resp.status_code == 404


async def test_list_practice_pool_excludes_flagged(session, client):
    """GET 练习池列表排除 is_flagged=True 的题（移出 practice pool）。"""
    doc_id, qids = await _seed_questions(session, n=3)
    await client.post(f"/api/questions/{qids[1]}/flag")  # 标记中间一题

    resp = await client.get(f"/api/documents/{doc_id}/questions")
    assert resp.status_code == 200, resp.text
    returned_ids = {q["id"] for q in resp.json()}
    assert qids[1] not in returned_ids  # 已标记 → 移出练习池
    assert qids[0] in returned_ids and qids[2] in returned_ids
    assert len(resp.json()) == 2


async def test_list_practice_pool_returns_unflagged_only(session, client):
    """练习池返回的题目 is_flagged 均为 False（已标记的不返回）。"""
    doc_id, _ = await _seed_questions(session, n=2)
    resp = await client.get(f"/api/documents/{doc_id}/questions")
    assert resp.status_code == 200
    for q in resp.json():
        assert q["is_flagged"] is False


async def test_list_practice_pool_unknown_doc_404(client):
    """查询不存在文档的练习池 → 404。"""
    resp = await client.get("/api/documents/9999/questions")
    assert resp.status_code == 404


async def test_list_practice_pool_empty_when_all_flagged(session, client):
    """全部题被标记 → 练习池为空列表（非 404，文档存在但无可用题）。"""
    doc_id, qids = await _seed_questions(session, n=2)
    await client.post(f"/api/questions/{qids[0]}/flag")
    await client.post(f"/api/questions/{qids[1]}/flag")
    resp = await client.get(f"/api/documents/{doc_id}/questions")
    assert resp.status_code == 200
    assert resp.json() == []
