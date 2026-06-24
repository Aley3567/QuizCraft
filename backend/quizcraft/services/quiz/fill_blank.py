"""填空题评分服务：normalize 后确定性匹配，不依赖 LLM。

对齐 DESIGN_DECISIONS 7.4：客观题即时判分（本地），离线可判、不消耗 LLM。
normalize 策略：NFKC 归一（全角→半角）+ 小写 + 去所有空白与标点（保留中文字与字母数字），
使 "光合作用。" 与 "光合作用"、"Photosynthesis" 与 "photosynthesis"、"类　囊 体" 与 "类囊体"
判等。学生答案 normalize 后与参考答案（answer_text）normalize 后相等 → 正确。

纯逻辑，不碰 DB：输入 duck-typed question（{answer_text}），返回 FillBlankScore。
落库由 router 负责；is_correct 用于客观题结算，score 留 None（避免与 is_correct 双重计入）。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# 去所有空白与非单词字符（标点），保留中文字符与字母数字（re.UNICODE 默认开，中文属 \w）
_NORMALIZE_STRIP_RE = re.compile(r"[\s\W_]+", re.UNICODE)


@dataclass
class FillBlankScore:
    """填空评分结果：确定性 is_correct（0/1），不依赖 LLM。"""

    is_correct: bool
    score: float


def _normalize_blank_answer(s: str | None) -> str:
    """归一化填空答案：NFKC 全角→半角、小写、去空白与标点，便于容错匹配。"""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.lower()
    return _NORMALIZE_STRIP_RE.sub("", s)


def score_fill_blank(question, *, student_answer: str) -> FillBlankScore:
    """确定性评分：学生答案 normalize 后等于参考答案（answer_text）normalize 后即正确。

    - 学生答案为空 / 参考答案缺失 → 判错（保守，不崩）。
    - 完全相等判对；部分包含不算对（避免"光合作用和呼吸作用"误判为"光合作用"）。
    """
    ref = (getattr(question, "answer_text", None) or "").strip()
    norm_ref = _normalize_blank_answer(ref)
    norm_student = _normalize_blank_answer(student_answer)
    is_correct = bool(norm_student) and norm_student == norm_ref
    return FillBlankScore(is_correct=is_correct, score=1.0 if is_correct else 0.0)
