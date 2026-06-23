"""测试用 PDF 生成助手：用 pymupdf 生成带真实文本层的内存 PDF。

用 china-s 内置 CJK 字体，确保中文可被 pymupdf4llm 提取（Helvetica 不嵌入 CJK 字形）。
test_parsing_pdf / test_documents_api 共用，避免重复。
"""
import pymupdf


def make_pdf_bytes(pages: list[list[tuple[float, str, int]]]) -> bytes:
    """生成内存 PDF。

    pages: 每页为 [(y, text, fontsize), ...] 文本行列表。
    返回 PDF 字节。
    """
    doc = pymupdf.open()
    for page_lines in pages:
        page = doc.new_page()
        for y, text, fontsize in page_lines:
            page.insert_text((72, y), text, fontsize=fontsize, fontname="china-s")
    data = doc.tobytes()
    doc.close()
    return data
