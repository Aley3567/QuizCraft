"""interleave_questions 纯函数单测（切片 1.2 子系统5 交叉出题）。

验证按 concept 交叉混合出题顺序：相邻题目尽量来自不同 concept，同 concept 题不聚集。
纯逻辑，不碰 DB / LLM。
"""
from quizcraft.services.quiz import GeneratedQuestion, interleave_questions


def _q(stem: str, concept_index: int, qtype: str = "multiple_choice") -> GeneratedQuestion:
    """构造最小 GeneratedQuestion，仅 concept_index / stem / question_type 参与交错。"""
    return GeneratedQuestion(
        section_index=0,
        concept_index=concept_index,
        concept_name=None,
        stem=stem,
        options=[],
        correct_option_index=None,
        explanation=None,
        bloom_level=None,
        difficulty=None,
        source_span={},
        question_type=qtype,
        answer_text=None,
    )


def test_interleave_empty():
    assert interleave_questions([]) == []


def test_interleave_single_unchanged():
    qs = [_q("A", 0)]
    assert interleave_questions(qs) == qs


def test_interleave_crosses_concepts():
    """2 concept 各 2 题 → 交错后相邻 concept 不同，同 concept 题不相邻，集合不变。"""
    a1, a2, b1, b2 = _q("A1", 0), _q("A2", 0), _q("B1", 1), _q("B2", 1)
    out = interleave_questions([a1, a2, b1, b2])
    assert len(out) == 4
    concepts = [q.concept_index for q in out]
    assert all(concepts[i] != concepts[i + 1] for i in range(len(concepts) - 1))
    assert {q.stem for q in out} == {"A1", "A2", "B1", "B2"}


def test_interleave_unbalanced_under_half():
    """3/2/1 分布（最大组未过半）→ round-robin 仍使相邻 concept 全不同，集合不变。"""
    qs = [
        _q("A1", 0),
        _q("A2", 0),
        _q("A3", 0),
        _q("B1", 1),
        _q("B2", 1),
        _q("C1", 2),
    ]
    out = interleave_questions(qs)
    concepts = [q.concept_index for q in out]
    assert all(concepts[i] != concepts[i + 1] for i in range(len(concepts) - 1))
    assert {q.stem for q in out} == {"A1", "A2", "A3", "B1", "B2", "C1"}


def test_interleave_preserves_set_and_length():
    """任意分布：交错不改变题目集合与数量，仅重排。"""
    qs = [_q("A1", 0), _q("A2", 0), _q("B1", 1), _q("B2", 1), _q("C1", 2)]
    out = interleave_questions(qs)
    assert len(out) == len(qs)
    assert {q.stem for q in out} == {q.stem for q in qs}


def test_interleave_stable_same_input_same_output():
    """同一输入两次交错结果一致（确定性，便于测试与可重现）。"""
    qs = [_q("A1", 0), _q("A2", 0), _q("B1", 1), _q("B2", 1)]
    assert interleave_questions(qs) == interleave_questions(list(qs))
