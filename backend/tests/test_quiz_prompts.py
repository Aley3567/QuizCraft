"""出题 prompt 构建测试：Step1 提取概念 / Step2 生成选择题 / 自评。

验证 prompt 要求 LLM 严格返回 JSON、来源锚定（source_text）、携带文档原文与页码章节。
prompt 只需 duck-typed 的 section / concept / question，不依赖 ORM。
"""
from types import SimpleNamespace

from quizcraft.services.parsing import SectionData
from quizcraft.services.quiz import (
    build_eval_messages,
    build_step1_messages,
    build_step2_messages,
)


def _section() -> SectionData:
    return SectionData(
        section_path="第2章 光合作用",
        page_number=12,
        content="光合作用是植物利用光能合成有机物的过程。光反应发生在类囊体膜上。",
        token_count=20,
        order_index=0,
    )


def test_step1_prompt_requires_json_with_source_text():
    """Step1 prompt 要求 JSON 输出 + source_text 溯源，并嵌入分块原文/页码/章节。"""
    msgs = build_step1_messages(_section(), n=5)
    assert len(msgs) == 2
    assert msgs[0].role == "system"
    assert msgs[1].role == "user"

    blob = msgs[0].content + msgs[1].content
    assert "JSON" in blob
    assert "source_text" in blob
    assert "5" in blob  # concepts_per_section
    assert _section().content in msgs[1].content
    assert "12" in msgs[1].content  # page_number
    assert "第2章 光合作用" in msgs[1].content


def test_step2_prompt_requires_options_and_source():
    """Step2 prompt 要求 options/correct_option_index/source_text，并嵌入概念名与原文。"""
    concept = SimpleNamespace(name="光合作用", description="植物利用光能合成有机物")
    msgs = build_step2_messages(concept, _section(), n=2)
    assert len(msgs) == 2

    blob = msgs[0].content + msgs[1].content
    assert "JSON" in blob
    assert "options" in blob
    assert "correct_option_index" in blob
    assert "source_text" in blob
    assert "光合作用" in msgs[1].content
    assert _section().content in msgs[1].content


def test_eval_prompt_scores_two_dimensions():
    """自评 prompt 只评 accuracy + source-grounding 两维度，要求 JSON。"""
    question = SimpleNamespace(
        stem="光反应发生在？",
        options=["细胞核", "类囊体膜", "细胞壁", "液泡"],
        correct_option_index=1,
        explanation="光反应在类囊体膜",
        source_span={"text": "光反应发生在类囊体膜上。"},
    )
    msgs = build_eval_messages(question, section_content=_section().content)
    assert len(msgs) == 2

    blob = msgs[0].content + msgs[1].content
    assert "accuracy" in blob
    assert "source_grounding" in blob
    assert "JSON" in blob
    assert "光反应发生在？" in msgs[1].content


def test_step1_prompt_supports_four_bloom_levels():
    """子系统2：Step1 prompt 支持完整 Bloom 四层（记忆/理解/应用/分析），不再只限记忆/理解。"""
    msgs = build_step1_messages(_section(), n=5)
    blob = msgs[0].content + msgs[1].content
    for level in ("记忆", "理解", "应用", "分析"):
        assert level in blob


def test_step2_prompt_constrains_difficulty_range():
    """子系统2：difficulty_range 传入后，Step2 prompt 约束 LLM 只用指定难度（含"只能取" + 指定值）。"""
    concept = SimpleNamespace(name="光合作用", description="植物利用光能合成有机物")
    msgs = build_step2_messages(concept, _section(), n=2, difficulty_range=["easy", "medium"])
    blob = msgs[0].content + msgs[1].content
    assert "easy" in blob
    assert "medium" in blob
    assert "只能取" in blob


def test_step2_prompt_conveys_bloom_distribution():
    """子系统2：bloom_distribution 传入后，Step2 prompt 体现分布比例与四层 Bloom。"""
    concept = SimpleNamespace(name="光合作用", description="植物利用光能合成有机物")
    dist = {"记忆": 0.4, "理解": 0.3, "应用": 0.2, "分析": 0.1}
    msgs = build_step2_messages(concept, _section(), n=2, bloom_distribution=dist)
    blob = msgs[0].content + msgs[1].content
    assert "记忆" in blob
    assert "应用" in blob
    assert "分析" in blob
    assert "40%" in blob  # 分布比例（0.4 → 40%）


def test_step2_prompt_default_includes_four_bloom_levels():
    """子系统2：默认（无 distribution）Step2 prompt 仍含完整四层 Bloom 可选层级。"""
    concept = SimpleNamespace(name="光合作用", description="植物利用光能合成有机物")
    msgs = build_step2_messages(concept, _section(), n=2)
    blob = msgs[0].content + msgs[1].content
    for level in ("记忆", "理解", "应用", "分析"):
        assert level in blob
