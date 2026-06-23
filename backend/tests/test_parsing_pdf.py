"""PDF 解析集成测试：用 pymupdf 生成带真实文本层的 PDF，跑真实 parse_pdf_to_sections。

不依赖外部 PDF 文件或真实 LLM——验证 L1 提取 + 结构感知分块端到端可用。
"""
from _pdf_helper import make_pdf_bytes

from quizcraft.services.parsing import parse_pdf_to_sections


async def test_parse_pdf_extracts_page_count_and_sections():
    """两页 PDF：解析出 page_count=2，至少一个 section，section 含提取的正文。"""
    pdf = make_pdf_bytes(
        [
            [(80, "第2章 光合作用", 18), (140, "光合作用是植物利用光能合成有机物的过程。", 11)],
            [(80, "光反应发生在类囊体膜上，暗反应在基质中。", 11)],
        ]
    )
    page_count, sections = parse_pdf_to_sections(pdf)

    assert page_count == 2
    assert len(sections) >= 1
    # 正文被提取进某个 section
    all_text = "\n".join(s.content for s in sections)
    assert "光合作用" in all_text
    assert "光反应" in all_text
    # 页码在合理范围
    assert all(s.page_number in (1, 2) for s in sections)


async def test_parse_pdf_sections_carry_page_and_path():
    """section 携带 page_number 与 section_path 元数据（错题引用的数据基础）。"""
    pdf = make_pdf_bytes(
        [
            [(80, "第2章 光合作用", 18), (140, "光合作用是植物利用光能合成有机物。", 11)],
        ]
    )
    _, sections = parse_pdf_to_sections(pdf)
    assert len(sections) >= 1
    section = sections[0]
    assert section.page_number == 1
    assert section.token_count > 0
    # 标题可能被 pymupdf4llm 识别为 # 标题，section_path 非空（含章节名）
    assert "光合作用" in (section.section_path + section.content)


async def test_parse_pdf_empty_pages_returns_empty():
    """无正文的 PDF 不产生 section（page_count 仍正确）。"""
    pdf = make_pdf_bytes([[]])
    page_count, sections = parse_pdf_to_sections(pdf)
    assert page_count == 1
    assert sections == []


async def test_parse_pdf_token_count_within_target():
    """多页长文本分块后每块 token_count 不超 max（1024）。"""
    sentence = "光合作用是植物利用光能将水和二氧化碳合成有机物并释放氧气的过程。"
    # 生成多页、每页多段，触发分块
    lines = [(80, "第2章 光合作用", 18)] + [
        (140 + i * 16, sentence, 11) for i in range(40)
    ]
    pdf = make_pdf_bytes([lines, [(80, sentence * 30, 11)]])
    _, sections = parse_pdf_to_sections(pdf)
    assert len(sections) >= 1
    for s in sections:
        assert s.token_count <= 1024
