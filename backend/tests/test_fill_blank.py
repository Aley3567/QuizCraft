"""填空题评分服务测试：确定性匹配（normalize 后相等），不依赖 LLM。

纯逻辑测试，不碰 DB——输入 duck-typed question（{stem, answer_text, source_span}）。
对齐 DESIGN_DECISIONS 7.4：客观题即时判分（本地），离线可判。
"""
from types import SimpleNamespace

from quizcraft.services.quiz.fill_blank import FillBlankScore, score_fill_blank

QUESTION = SimpleNamespace(
    stem="光反应发生在____上。",
    answer_text="类囊体膜",
    source_span={"text": "光反应发生在类囊体膜上。", "page": 12, "section_path": "第2章 光合作用"},
)


def test_exact_match_correct():
    """学生答案与参考答案完全一致 → is_correct=True，score=1.0。"""
    r = score_fill_blank(QUESTION, student_answer="类囊体膜")
    assert isinstance(r, FillBlankScore)
    assert r.is_correct is True
    assert r.score == 1.0


def test_mismatch_incorrect():
    """学生答案与参考答案无关 → is_correct=False，score=0.0。"""
    r = score_fill_blank(QUESTION, student_answer="细胞核")
    assert r.is_correct is False
    assert r.score == 0.0


def test_case_insensitive():
    """英文答案大小写不敏感（Photosynthesis == photosynthesis）。"""
    q = SimpleNamespace(stem="植物合成有机物的过程称为____。", answer_text="Photosynthesis")
    assert score_fill_blank(q, student_answer="photosynthesis").is_correct is True


def test_punctuation_tolerated():
    """标点容忍：学生答案带句号与参考答案匹配（光合作用。== 光合作用）。"""
    q = SimpleNamespace(stem="植物利用光能合成有机物的过程是____", answer_text="光合作用")
    assert score_fill_blank(q, student_answer="光合作用。").is_correct is True
    assert score_fill_blank(q, student_answer="，光合作用！").is_correct is True


def test_whitespace_tolerated():
    """空白容忍：前后空格与中间空格不影响匹配。"""
    q = SimpleNamespace(stem="x", answer_text="类囊体膜")
    assert score_fill_blank(q, student_answer="  类囊体膜  ").is_correct is True
    # 全角空格 NFKC 归一为半角空格后被去除
    assert score_fill_blank(q, student_answer="类　囊　体膜").is_correct is True


def test_full_width_to_half_width():
    """全角字母数字归一为半角后匹配（ＡＢＣ == ABC）。"""
    q = SimpleNamespace(stem="x", answer_text="ABC")
    assert score_fill_blank(q, student_answer="ＡＢＣ").is_correct is True


def test_empty_student_answer_incorrect():
    """空学生答案 → is_correct=False（不与参考答案匹配）。"""
    assert score_fill_blank(QUESTION, student_answer="").is_correct is False
    assert score_fill_blank(QUESTION, student_answer="   ").is_correct is False


def test_missing_reference_answer_incorrect():
    """参考答案缺失（answer_text=None/空）→ is_correct=False，不崩（保守判错）。"""
    q_none = SimpleNamespace(stem="x", answer_text=None)
    q_empty = SimpleNamespace(stem="x", answer_text="")
    assert score_fill_blank(q_none, student_answer="任何答案").is_correct is False
    assert score_fill_blank(q_empty, student_answer="任何答案").is_correct is False


def test_partial_match_still_incorrect():
    """部分包含不判对：学生答案仅含参考答案子串不算正确（精确 normalize 相等才对）。"""
    q = SimpleNamespace(stem="x", answer_text="光合作用")
    assert score_fill_blank(q, student_answer="光合作用和呼吸作用").is_correct is False


def test_score_is_zero_or_one():
    """填空题评分为确定性 0/1（非连续值），便于客观题结算按 is_correct 计 1。"""
    assert score_fill_blank(QUESTION, student_answer="类囊体膜").score == 1.0
    assert score_fill_blank(QUESTION, student_answer="错").score == 0.0
