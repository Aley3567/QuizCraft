"""Token 数估算（粗略，用于结构分块的尺寸控制，非计费口径）。

切片 1.1 不引入 tiktoken 依赖：中文按每字 ≈1 token，其余按每 4 字符 ≈1 token
（英文常用比例）。这是分块尺寸控制的近似值；出题/成本计费的真实 token 留给切片 1.2。
"""
from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """估算文本 token 数。

    - CJK 汉字（U+4E00..U+9FFF 基本块）按每字 ≈1 token（多数 tokenizer 下中文每字 1-2 token，取 1 偏保守，分块更小）。
    - 其余字符按每 4 字符 ≈1 token（英文经验比例）。

    用 ord() 比较码点，避免源码中出现 CJK 字面量带来的歧义。
    """
    if not text:
        return 0
    cjk = sum(1 for ch in text if 0x4E00 <= ord(ch) <= 0x9FFF)
    rest = len(text) - cjk
    return cjk + rest // 4
