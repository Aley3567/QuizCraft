"""L1 PDF 解析器：PyMuPDF4LLM 提取文本 + 基本结构，再交给 chunker 结构感知分块。

对齐 DESIGN_DECISIONS 4.1 的 L1 快速层：用 pymupdf4llm 经典 markdown 提取
（关闭 layout+OCR 重管线——干净数字 PDF 无需 OCR），每页带页码，标题转 markdown 标题。
L2（Docling）/L3（视觉 LLM）分层路由留给切片 1.4。
"""
from __future__ import annotations

import pymupdf
import pymupdf4llm

from quizcraft.services.parsing.chunker import PageMarkdown, SectionData, chunk_pages

# 切到经典 markdown 提取路径：关闭 layout+OCR 重管线，避免对干净数字 PDF 误走 Tesseract。
# 模块级一次性切换（pymupdf4llm 内部以全局 _use_layout 开关路由）。
pymupdf4llm.use_layout(False)


def parse_pdf_to_sections(pdf_bytes: bytes) -> tuple[int, list[SectionData]]:
    """解析 PDF 字节为结构感知分块。

    返回 (page_count, sections)。page_count 来自 PDF 元信息；sections 按 chunk_pages 切分。
    切片 1.1 仅做内存解析，不落盘原文件（reparse 留给切片 1.4）。
    """
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        page_count = doc.page_count
        pages = _extract_pages(doc)
    finally:
        doc.close()

    sections = chunk_pages(pages)
    return page_count, sections


def _extract_pages(doc: pymupdf.Document) -> list[PageMarkdown]:
    """用 pymupdf4llm 经典路径按页提取 markdown 文本。"""
    chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)
    pages: list[PageMarkdown] = []
    for chunk in chunks:
        # 经典路径 metadata 用 "page"（1-indexed）
        page_number = int(chunk.get("metadata", {}).get("page", len(pages) + 1))
        text = chunk.get("text", "") or ""
        pages.append(PageMarkdown(page_number=page_number, text=text))
    return pages
