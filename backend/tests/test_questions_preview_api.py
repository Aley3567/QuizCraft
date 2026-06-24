"""题目预览编辑 API 测试（切片 1.2 子系统4）。

- PUT /api/questions/{id}：编辑题干/选项/正确答案/参考答案/解析（按题型校验）
- DELETE /api/questions/{id}：删除题（清理引用它的 QuizSession.question_ids，Answer 级联删）
- POST /api/questions/{id}/publish：确认进池（in_practice_pool=True，幂等）
- GET /api/documents/{id}/questions/drafts：预览草稿题（in_practice_pool=False）
- 出题 auto_publish=False 生成草稿 → 预览/确认进池 端到端（复用 llm_mock 走真实 generate-quiz）

绕过出题：直接 ORM 插 Document+Section+Question，聚焦编辑/删除/确认语义，不依赖 LLM
（草稿端到端用例除外）。
"""
from sqlalchemy import select

from quizcraft.models.document import Document, DocumentStatus, Section
from quizcraft.models.quiz import (
    Question,
    QuestionType,
    QuizSession,
    SessionStatus,
)


async def _seed_one_question(
    session,
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
    in_practice_pool: bool = True,
) -> tuple[int, int]:
    """直接插一道题 + 所属文档/分块，返回 (document_id, question_id)。"""
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
    is_mc = question_type == QuestionType.MULTIPLE_CHOICE
    q = Question(
        document_id=doc.id,
        concept_id=None,
        section_id=section.id,
        question_type=question_type,
        stem="原题干",
        options=["A", "B", "C", "D"] if is_mc else [],
        correct_option_index=0 if is_mc else None,
        answer_text="参考答案" if not is_mc else None,
        explanation="原解析",
        source_span={"page": 12, "section_path": "第2章", "text": "光合作用内容"},
        bloom_level="记忆",
        difficulty="easy",
        in_practice_pool=in_practice_pool,
    )
    session.add(q)
    await session.flush()
    await session.commit()
    return doc.id, q.id


# ===== 编辑 =====


async def test_update_question_stem_and_options(session, client):
    """PUT 编辑选择题：改题干/选项/正确答案/解析 → 落库 + 返回更新后内容。"""
    _, qid = await _seed_one_question(session)
    resp = await client.put(
        f"/api/questions/{qid}",
        json={
            "stem": "新题干",
            "options": ["X", "Y", "Z"],
            "correct_option_index": 2,
            "explanation": "新解析",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stem"] == "新题干"
    assert body["options"] == ["X", "Y", "Z"]
    assert body["correct_option_index"] == 2
    assert body["explanation"] == "新解析"

    q = (await session.execute(select(Question).where(Question.id == qid))).scalar_one()
    assert q.stem == "新题干"
    assert q.options == ["X", "Y", "Z"]
    assert q.correct_option_index == 2


async def test_update_question_partial_keeps_others(session, client):
    """部分更新：只改题干，options/correct 保留原值。"""
    _, qid = await _seed_one_question(session)
    resp = await client.put(f"/api/questions/{qid}", json={"stem": "只改题干"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stem"] == "只改题干"
    assert body["options"] == ["A", "B", "C", "D"]  # 保留
    assert body["correct_option_index"] == 0  # 保留
    assert body["explanation"] == "原解析"  # 保留


async def test_update_question_short_answer_answer_text(session, client):
    """PUT 编辑简答题 answer_text/stem → 落库。"""
    _, qid = await _seed_one_question(session, question_type=QuestionType.SHORT_ANSWER)
    resp = await client.put(
        f"/api/questions/{qid}",
        json={"stem": "新简答题干", "answer_text": "新参考答案"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stem"] == "新简答题干"
    assert body["answer_text"] == "新参考答案"


async def test_update_question_correct_index_out_of_range_422(session, client):
    """选择题 correct_option_index 超出选项范围 → 422。"""
    _, qid = await _seed_one_question(session)
    resp = await client.put(
        f"/api/questions/{qid}",
        json={"correct_option_index": 99},
    )
    assert resp.status_code == 422


async def test_update_question_short_answer_missing_answer_text_422(session, client):
    """简答题编辑后无 answer_text → 422（清空参考答案不合法）。"""
    _, qid = await _seed_one_question(session, question_type=QuestionType.SHORT_ANSWER)
    # answer_text=None 表示不更新；用空串显式清空 → 校验失败
    resp = await client.put(f"/api/questions/{qid}", json={"answer_text": "   "})
    assert resp.status_code == 422


async def test_update_question_unknown_404(client):
    """编辑不存在的题 → 404。"""
    resp = await client.put("/api/questions/9999", json={"stem": "x"})
    assert resp.status_code == 404


# ===== 删除 =====


async def test_delete_question_removes_from_db(session, client):
    """DELETE → 204，题从 DB 删除。"""
    _, qid = await _seed_one_question(session)
    resp = await client.delete(f"/api/questions/{qid}")
    assert resp.status_code == 204, resp.text
    q = (
        await session.execute(select(Question).where(Question.id == qid))
    ).scalar_one_or_none()
    assert q is None


async def test_delete_question_unknown_404(client):
    """删除不存在的题 → 404。"""
    resp = await client.delete("/api/questions/9999")
    assert resp.status_code == 404


async def test_delete_question_cleans_referencing_sessions(session, client, engine):
    """删除题后，引用它的 QuizSession.question_ids 移除该 id（结算不残留已删题）。

    用全新 session 读 DB 真实值，绕过 seed 时建的测试 session identity map 缓存。
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    doc_id, qid = await _seed_one_question(session)
    quiz = QuizSession(
        document_id=doc_id,
        question_ids=[qid, 9998],  # 含被删题 + 另一占位
        status=SessionStatus.IN_PROGRESS,
        total=2,
    )
    session.add(quiz)
    await session.commit()
    quiz_id = quiz.id

    resp = await client.delete(f"/api/questions/{qid}")
    assert resp.status_code == 204, resp.text

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as fresh_session:
        fresh = (
            await fresh_session.execute(
                select(QuizSession).where(QuizSession.id == quiz_id)
            )
        ).scalar_one()
        assert qid not in (fresh.question_ids or [])
        assert 9998 in fresh.question_ids  # 其他题保留


# ===== 确认进池 =====


async def test_publish_question_moves_to_pool(session, client):
    """POST publish → in_practice_pool=True，幂等（重复仍 True）。"""
    _, qid = await _seed_one_question(session, in_practice_pool=False)
    resp = await client.post(f"/api/questions/{qid}/publish")
    assert resp.status_code == 200, resp.text
    assert resp.json()["in_practice_pool"] is True

    resp2 = await client.post(f"/api/questions/{qid}/publish")
    assert resp2.status_code == 200
    assert resp2.json()["in_practice_pool"] is True

    q = (await session.execute(select(Question).where(Question.id == qid))).scalar_one()
    assert q.in_practice_pool is True


async def test_publish_unknown_404(client):
    """确认不存在的题 → 404。"""
    resp = await client.post("/api/questions/9999/publish")
    assert resp.status_code == 404


# ===== 草稿列表 =====


async def test_list_drafts_excludes_published(session, client):
    """GET /drafts 只返回草稿题（in_practice_pool=False）。"""
    doc = Document(filename="lecture.pdf", page_count=1, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()
    section = Section(
        document_id=doc.id,
        section_path="第2章",
        page_number=12,
        content="c",
        order_index=0,
        token_count=10,
    )
    session.add(section)
    await session.flush()
    draft_q = Question(
        document_id=doc.id,
        section_id=section.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        stem="草稿题",
        options=["a", "b"],
        correct_option_index=0,
        explanation="",
        source_span={"page": 1},
        in_practice_pool=False,
    )
    pub_q = Question(
        document_id=doc.id,
        section_id=section.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        stem="已进池题",
        options=["a", "b"],
        correct_option_index=0,
        explanation="",
        source_span={"page": 1},
        in_practice_pool=True,
    )
    session.add_all([draft_q, pub_q])
    await session.commit()

    resp = await client.get(f"/api/documents/{doc.id}/questions/drafts")
    assert resp.status_code == 200, resp.text
    stems = {q["stem"] for q in resp.json()}
    assert "草稿题" in stems
    assert "已进池题" not in stems


async def test_list_drafts_unknown_doc_404(client):
    """查不存在文档的草稿 → 404。"""
    resp = await client.get("/api/documents/9999/questions/drafts")
    assert resp.status_code == 404


# ===== 端到端：草稿生成 → 确认进池 =====


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


async def test_generate_draft_then_publish_into_pool(session, client, llm_mock):
    """端到端：auto_publish=False 生成草稿题 → GET /drafts 可见 + 练习池不可见
    → publish → 练习池可见（验证「预览→确认进池」完整闭环）。"""
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
    llm_mock.set_responses([STEP1, STEP2, EVAL_HIGH])

    resp = await client.post(
        f"/api/documents/{doc.id}/generate-quiz",
        json={"auto_publish": False},
    )
    assert resp.status_code == 201, resp.text
    q = resp.json()["questions"][0]
    qid = q["id"]
    assert q["in_practice_pool"] is False  # 草稿

    # 草稿列表可见
    drafts = (await client.get(f"/api/documents/{doc.id}/questions/drafts")).json()
    assert any(d["id"] == qid for d in drafts)

    # 练习池不可见
    pool = (await client.get(f"/api/documents/{doc.id}/questions")).json()
    assert all(p["id"] != qid for p in pool)

    # 确认进池
    pub = await client.post(f"/api/questions/{qid}/publish")
    assert pub.status_code == 200
    assert pub.json()["in_practice_pool"] is True

    # 练习池现在可见
    pool2 = (await client.get(f"/api/documents/{doc.id}/questions")).json()
    assert any(p["id"] == qid for p in pool2)


async def test_generate_default_auto_publishes(session, client, llm_mock):
    """默认 auto_publish=True：生成即进池（保留切片 1.1 生成→可答闭环），练习池直接可见。"""
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
    llm_mock.set_responses([STEP1, STEP2, EVAL_HIGH])

    resp = await client.post(f"/api/documents/{doc.id}/generate-quiz")
    assert resp.status_code == 201, resp.text
    q = resp.json()["questions"][0]
    assert q["in_practice_pool"] is True  # 默认进池

    pool = (await client.get(f"/api/documents/{doc.id}/questions")).json()
    assert any(p["id"] == q["id"] for p in pool)
