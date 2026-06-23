"""文档上传与查询 API 测试：真实生成 PDF 走 POST /api/documents 全流程，SQLite 内存。

不依赖真实 LLM（解析阶段无 LLM 调用）。
"""
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from _pdf_helper import make_pdf_bytes


def _lecture_pdf() -> bytes:
    """生成一份两页中文课件 PDF，含标题与正文。"""
    return make_pdf_bytes(
        [
            [(80, "第2章 光合作用", 18), (140, "光合作用是植物利用光能合成有机物的过程。", 11)],
            [(80, "光反应发生在类囊体膜上，暗反应在基质中。", 11)],
        ]
    )


async def test_upload_pdf_returns_document_with_sections(client):
    """POST /api/documents 上传 PDF → 201，返回文档详情含 page_count 与非空 sections。"""
    pdf = _lecture_pdf()
    resp = await client.post(
        "/api/documents",
        files={"file": ("lecture.pdf", pdf, "application/pdf")},
    )
    assert resp.status_code == HTTP_201_CREATED, resp.text
    body = resp.json()
    assert body["filename"] == "lecture.pdf"
    assert body["page_count"] == 2
    assert body["status"] == "complete"
    assert body["section_count"] == len(body["sections"]) >= 1
    section = body["sections"][0]
    assert "section_path" in section
    assert "page_number" in section
    assert section["content"]
    assert section["token_count"] > 0


async def test_uploaded_sections_carry_page_and_section_path(client):
    """上传后 section 携带 page_number 与 section_path（错题溯源的数据基础）。"""
    pdf = _lecture_pdf()
    resp = await client.post(
        "/api/documents",
        files={"file": ("lecture.pdf", pdf, "application/pdf")},
    )
    body = resp.json()
    all_text = "".join(s["content"] for s in body["sections"])
    assert "光合作用" in all_text
    # page_number 落在合理范围
    assert all(s["page_number"] in (1, 2) for s in body["sections"])


async def test_get_document_returns_detail(client):
    """GET /api/documents/{id} 返回文档详情，sections 按 order_index 排序。"""
    pdf = _lecture_pdf()
    created = await client.post(
        "/api/documents",
        files={"file": ("lecture.pdf", pdf, "application/pdf")},
    )
    doc_id = created.json()["id"]

    resp = await client.get(f"/api/documents/{doc_id}")
    assert resp.status_code == HTTP_200_OK
    body = resp.json()
    assert body["id"] == doc_id
    assert body["filename"] == "lecture.pdf"
    assert body["status"] == "complete"
    assert len(body["sections"]) >= 1
    order_indices = [s["order_index"] for s in body["sections"]]
    assert order_indices == sorted(order_indices)


async def test_get_unknown_document_returns_404(client):
    """GET 不存在的文档 id 返回 404。"""
    resp = await client.get("/api/documents/9999")
    assert resp.status_code == 404


async def test_upload_non_pdf_rejected(client):
    """POST 非 PDF（.txt）返回 400，不创建文档。"""
    resp = await client.post(
        "/api/documents",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )
    assert resp.status_code == 400
