"""Token 估算测试：中文按字、英文按 4 字符比例，空串归零。"""
from quizcraft.services.parsing import estimate_tokens


def test_empty_text_is_zero():
    assert estimate_tokens("") == 0


def test_pure_chinese_counts_chars():
    # 「光合作用」4 个汉字，每字 ≈1 token
    assert estimate_tokens("光合作用") == 4


def test_pure_english_uses_four_char_ratio():
    # 12 个 ASCII 字符，12 // 4 = 3
    assert estimate_tokens("hello world!") == 3


def test_mixed_text():
    # 4 汉字 + " hello!"（7 ASCII）→ 4 + 7//4 = 4 + 1 = 5
    assert estimate_tokens("光合作用 hello!") == 5


def test_whitespace_contributes_via_rest_floor():
    # 4 汉字 + 4 空格 → 4 + 4//4 = 4 + 1 = 5（空格进 rest，不单独计费）
    assert estimate_tokens("光合作用    ") == 5
