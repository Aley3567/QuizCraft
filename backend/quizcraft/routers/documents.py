"""文档上传与查询路由。

POST /api/documents：接受 PDF，L1 解析 + 结构分块，落库 Document -> Sections。
GET /api/documents/{id}：取文档详情（含 sections）。

切片 1.1 在请求内同步解析（小 PDF 秒级完成，满足「2 分钟内」验收）；
异步解析 + 进度轮询（status pending->processing->complete）留给切片 1.4。
原文件落盘也留给切片 1.4 的 reparse，切片 1.1 仅解析内存字节，storage_path 留空。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.dependencies import get_session
from quizcraft.models.document import Document, DocumentStatus, Section
from quizcraft.schemas.document import DocumentDetail, SectionOut
from quizcraft.services.parsing import parse_pdf_to_sections

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _is_pdf(file: UploadFile) -> bool:
    """按扩展名或 content-type 判定是否 PDF。"""
    name = (file.filename or "").lower()
    if name.endswith(".pdf"):
        return True
    return (file.content_type or "").lower() == "application/pdf"


@router.post("", response_model=DocumentDetail, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> DocumentDetail:
    """上传 PDF：解析 + 结构分块 + 落库，返回文档详情。"""
    if not _is_pdf(file):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    pdf_bytes = await file.read()

    doc = Document(
        filename=file.filename or "upload.pdf",
        status=DocumentStatus.PROCESSING,
    )
    session.add(doc)
    await session.flush()  # 取 doc.id

    try:
        page_count, sections = parse_pdf_to_sections(pdf_bytes)
    except Exception as exc:  # noqa: BLE001 解析失败需向调用方透传原因
        doc.status = DocumentStatus.FAILED
        await session.commit()
        raise HTTPException(status_code=422, detail=f"PDF 解析失败: {exc}") from exc

    doc.page_count = page_count
    doc.status = DocumentStatus.COMPLETE
    section_objs = [
        Section(
            document_id=doc.id,
            section_path=s.section_path,
            page_number=s.page_number,
            content=s.content,
            token_count=s.token_count,
            order_index=s.order_index,
        )
        for s in sections
    ]
    session.add_all(section_objs)
    await session.flush()  # 取 section id
    await session.commit()
    await session.refresh(doc)  # 填充 server-side created_at

    return DocumentDetail(
        id=doc.id,
        filename=doc.filename,
        page_count=doc.page_count,
        status=doc.status,
        section_count=len(section_objs),
        created_at=doc.created_at,
        sections=[SectionOut.model_validate(s) for s in section_objs],
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
) -> DocumentDetail:
    """取文档详情（含按 order_index 排序的 sections）。"""
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    result = await session.execute(
        select(Section)
        .where(Section.document_id == document_id)
        .order_by(Section.order_index)
    )
    sections = result.scalars().all()

    return DocumentDetail(
        id=doc.id,
        filename=doc.filename,
        page_count=doc.page_count,
        status=doc.status,
        section_count=len(sections),
        created_at=doc.created_at,
        sections=[SectionOut.model_validate(s) for s in sections],
    )


__all__ = ["router"]
