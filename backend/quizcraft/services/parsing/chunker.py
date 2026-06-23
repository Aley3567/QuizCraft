"""结构感知分块：把 PDF 提取的 markdown 按 512-1024 token 切分，保留 section_path 与 page_number。

分块策略（对齐 DESIGN_DECISIONS 4.1）：
- 按章节/标题切：维护 header 栈，section_path = 标题以 " > " 连接，跨页保持。
- 命中标题前先冲刷当前缓冲，保证一个 chunk 不跨越章节边界。
- 缓冲超过 max_tokens 时按段落 → 句子 → 字符 三级回退拆分，保证每块不超上限。
- 短章节允许小于 min_tokens（不强行合并跨章节），min_tokens 仅作软目标。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from quizcraft.services.parsing.tokens import estimate_tokens

HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？.!?])")

DEFAULT_MIN_TOKENS = 512
DEFAULT_MAX_TOKENS = 1024


@dataclass
class PageMarkdown:
    """pymupdf4llm 单页提取结果。page_number 为 1-indexed。"""

    page_number: int
    text: str


@dataclass
class SectionData:
    """结构感知分块产物，一一对应 ORM Section 行。"""

    section_path: str
    page_number: int
    content: str
    token_count: int
    order_index: int = 0


@dataclass
class _HeaderStack:
    """按层级维护当前标题路径，模拟 markdown TOC 嵌套。"""

    _stack: list[tuple[int, str]] = field(default_factory=list)

    def push(self, level: int, title: str) -> None:
        # 同级或更深的标题先弹出，再压入新标题，保证嵌套正确
        while self._stack and self._stack[-1][0] >= level:
            self._stack.pop()
        self._stack.append((level, title))

    def path(self) -> str:
        return " > ".join(title for _, title in self._stack)


def chunk_pages(
    pages: list[PageMarkdown],
    *,
    min_tokens: int = DEFAULT_MIN_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[SectionData]:
    """把多页 markdown 切成结构感知分块。

    pages 按页码顺序传入；header 栈跨页维护，section_path 在缓冲开始时捕获。
    """
    sections: list[SectionData] = []
    headers = _HeaderStack()
    buffer: list[str] = []
    buffer_path = ""
    buffer_page = 0

    def flush() -> None:
        nonlocal buffer, buffer_path, buffer_page
        if not buffer:
            return
        text = "\n".join(buffer).strip()
        if text:
            for chunk_text, token_count in _split_to_max(text, max_tokens):
                sections.append(
                    SectionData(
                        section_path=buffer_path,
                        page_number=buffer_page,
                        content=chunk_text,
                        token_count=token_count,
                        order_index=len(sections),
                    )
                )
        buffer = []

    for page in pages:
        for line in page.text.split("\n"):
            header = HEADER_RE.match(line)
            if header:
                # 切换章节前先落盘当前缓冲，保证 chunk 不跨章节
                flush()
                level = len(header.group(1))
                headers.push(level, header.group(2).strip())
            elif line.strip():
                if not buffer:
                    buffer_path = headers.path()
                    buffer_page = page.page_number
                buffer.append(line.strip())
        # 跨页继续累积同一章节内容；page_number 取缓冲起始页
    flush()
    return sections


def _split_to_max(text: str, max_tokens: int) -> list[tuple[str, int]]:
    """把超长文本切成不超过 max_tokens 的块，尽量在段落/句子边界断开。"""
    est = estimate_tokens(text)
    if est <= max_tokens:
        return [(text, est)]

    units = _split_units(text)
    chunks: list[str] = []
    cur = ""
    for unit in units:
        if estimate_tokens(unit) > max_tokens:
            # 单个单元就超限：先落盘当前，再对它做硬切
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.extend(_hard_char_split(unit, max_tokens))
            continue
        # 对候选拼接后的真实字符串估算（而非逐单元累加）：拼接引入的 \n\n 与标点
        # 经 rest//4 进位会让真实 token 数高于累加值，必须用真实值判断边界。
        candidate = (cur + "\n\n" + unit) if cur else unit
        if cur and estimate_tokens(candidate) > max_tokens:
            chunks.append(cur)
            cur = unit
        else:
            cur = candidate
    if cur:
        chunks.append(cur)
    return [(c, estimate_tokens(c)) for c in chunks]


def _split_units(text: str) -> list[str]:
    """优先按段落切；无段落则按句切；都不行则整体作为一个单元。"""
    paras = [p for p in text.split("\n\n") if p.strip()]
    if len(paras) >= 2:
        return paras
    sents = [s for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if len(sents) >= 2:
        return sents
    return [text]


def _hard_char_split(text: str, max_tokens: int) -> list[str]:
    """逐字累积直到达到 max_tokens，作为最终回退拆分（极少触发）。"""
    out: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if estimate_tokens(cur) >= max_tokens:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out
