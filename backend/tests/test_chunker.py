"""结构感知分块测试：header 栈、跨页 section_path、512-1024 token 边界、超限拆分。"""
import pytest

from quizcraft.services.parsing import DEFAULT_MAX_TOKENS, PageMarkdown, chunk_pages


def _make_pages(*pairs: tuple[int, str]) -> list[PageMarkdown]:
    return [PageMarkdown(page_number=pn, text=text) for pn, text in pairs]


def test_single_section_no_header():
    """无标题时 section_path 为空，整段作为一个 chunk。"""
    pages = _make_pages((1, "光合作用是植物利用光能合成有机物的过程。\n"))
    sections = chunk_pages(pages)
    assert len(sections) == 1
    assert sections[0].section_path == ""
    assert sections[0].page_number == 1
    assert "光合作用" in sections[0].content
    assert sections[0].order_index == 0


def test_header_sets_section_path():
    """标题行更新 section_path，正文归入该路径。"""
    pages = _make_pages((1, "# 第2章 光合作用\n\n光合作用是植物利用光能合成有机物。\n"))
    sections = chunk_pages(pages)
    assert len(sections) == 1
    assert sections[0].section_path == "第2章 光合作用"
    assert "光合作用是植物利用光能合成有机物" in sections[0].content
    # 标题本身不进 content
    assert "第2章 光合作用" not in sections[0].content


def test_nested_headers_build_path():
    """多级标题嵌套：# A > ## B 形成 "A > B" 路径。"""
    md = "# 第2章 光合作用\n\n## 2.1 概念\n\n光合作用是植物利用光能合成有机物。\n"
    pages = _make_pages((1, md))
    sections = chunk_pages(pages)
    assert len(sections) == 1
    assert sections[0].section_path == "第2章 光合作用 > 2.1 概念"


def test_sibling_header_replaces_nested_context():
    """同级新标题替换同级旧上下文：## A 后 ## B，B 不再挂在 A 下。"""
    md = (
        "# 第2章 光合作用\n\n## 2.1 概念\n\n光合作用概念。\n\n"
        "## 2.2 光反应\n\n光反应发生在类囊体膜上。\n"
    )
    pages = _make_pages((1, md))
    sections = chunk_pages(pages)
    paths = [s.section_path for s in sections]
    assert "第2章 光合作用 > 2.1 概念" in paths
    assert "第2章 光合作用 > 2.2 光反应" in paths


def test_section_path_carries_across_pages():
    """标题跨页保持：第 1 页标题后，第 2 页无标题内容仍归入该路径。"""
    pages = _make_pages(
        (1, "# 第2章 光合作用\n\n光合作用是植物利用光能合成有机物的过程。\n"),
        (2, "光反应发生在类囊体膜上，暗反应发生在基质中。\n"),
    )
    sections = chunk_pages(pages)
    # 跨页同章节合并为一个 chunk
    assert len(sections) == 1
    assert sections[0].section_path == "第2章 光合作用"
    assert sections[0].page_number == 1  # 取缓冲起始页
    assert "光反应" in sections[0].content


def test_new_header_on_next_page_flushes_buffer():
    """第 2 页出现新标题时，第 1 页内容先落盘，不混入新章节。"""
    pages = _make_pages(
        (1, "# 2.1 概念\n\n光合作用概念内容。\n"),
        (2, "# 2.2 光反应\n\n光反应内容。\n"),
    )
    sections = chunk_pages(pages)
    assert len(sections) == 2
    assert sections[0].section_path == "2.1 概念"
    assert sections[0].page_number == 1
    assert sections[1].section_path == "2.2 光反应"
    assert sections[1].page_number == 2


def test_oversized_section_splits_within_max_tokens():
    """单段超 max_tokens 时按段落/句子拆分，每块不超上限。"""
    sentence = "光合作用是植物利用光能将水和二氧化碳合成有机物并释放氧气的过程。"
    big_single = sentence * 40  # 40 * ~31 字 ≈ 1240 token，单段超过 1024
    pages = _make_pages((1, "# 大段\n\n" + big_single + "\n"))
    sections = chunk_pages(pages, max_tokens=1024)
    assert len(sections) >= 2
    for s in sections:
        assert s.token_count <= DEFAULT_MAX_TOKENS
        assert s.section_path == "大段"


def test_order_index_is_sequential():
    """多块 order_index 从 0 递增。"""
    md = "# A\n\n内容一。\n\n# B\n\n内容二。\n"
    pages = _make_pages((1, md))
    sections = chunk_pages(pages)
    assert [s.order_index for s in sections] == list(range(len(sections)))


def test_short_section_allowed_below_min():
    """短章节允许小于 min_tokens（不强行跨章节合并）。"""
    pages = _make_pages((1, "# 短\n\n一句话。\n"))
    sections = chunk_pages(pages, min_tokens=512)
    assert len(sections) == 1
    assert sections[0].token_count < 512
    assert sections[0].section_path == "短"


def test_blank_lines_are_ignored():
    """空行不产生空 chunk。"""
    pages = _make_pages((1, "\n\n\n# A\n\n\n\n正文\n\n\n"))
    sections = chunk_pages(pages)
    assert len(sections) == 1
    assert sections[0].content == "正文"
