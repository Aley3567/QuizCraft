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


def test_eval_prompt_scores_six_dimensions():
    """子系统6：自评 prompt 评完整 6 维度（accuracy/clarity/difficulty/source_grounding/non_trivial/non_ambiguous）。"""
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
    for dim in (
        "accuracy",
        "clarity",
        "difficulty",
        "source_grounding",
        "non_trivial",
        "non_ambiguous",
    ):
        assert dim in blob
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


def test_step2_short_answer_prompt_requires_answer_rubric_and_source():
    """子系统3：简答 Step2 prompt 要求 answer_text（参考答案/rubric）+ source_text 锚定，不要求 options。"""
    from quizcraft.services.quiz.prompts import build_step2_short_answer_messages

    concept = SimpleNamespace(name="光合作用", description="植物利用光能合成有机物")
    msgs = build_step2_short_answer_messages(concept, _section(), n=2)
    assert len(msgs) == 2

    blob = msgs[0].content + msgs[1].content
    assert "JSON" in blob
    assert "answer_text" in blob  # 参考答案/rubric
    assert "source_text" in blob  # 来源锚定
    assert "options" not in blob  # 简答题无选项
    assert "short_answer" in blob  # 明确简答题型
    assert "光合作用" in msgs[1].content
    assert _section().content in msgs[1].content


def test_short_answer_eval_prompt_uses_rubric_and_student_answer():
    """子系统3：简答评分 prompt 以参考答案为 rubric + 学生作答 + 文档原文，要求 score(0-1) + feedback。"""
    from quizcraft.services.quiz.prompts import build_short_answer_eval_messages

    question = SimpleNamespace(
        stem="简述光反应的发生部位。",
        answer_text="光反应发生在类囊体膜上，负责水的光解与 ATP/NADPH 的生成。",
        source_span={"text": "光反应发生在类囊体膜上。", "page": 12, "section_path": "第2章"},
    )
    msgs = build_short_answer_eval_messages(
        question, student_answer="光反应在细胞核里进行", section_content=_section().content
    )
    assert len(msgs) == 2

    blob = msgs[0].content + msgs[1].content
    assert "score" in blob
    assert "feedback" in blob
    assert "JSON" in blob
    # rubric（参考答案）与学生作答均嵌入
    assert "类囊体膜" in msgs[1].content
    assert "细胞核里进行" in msgs[1].content


def test_step2_fill_blank_prompt_requires_answer_and_source():
    """子系统2：填空 Step2 prompt 要求 answer_text（参考答案）+ source_text 锚定 + 占位，不要求 options。"""
    from quizcraft.services.quiz.prompts import build_step2_fill_blank_messages

    concept = SimpleNamespace(name="光合作用", description="植物利用光能合成有机物")
    msgs = build_step2_fill_blank_messages(concept, _section(), n=2)
    assert len(msgs) == 2

    blob = msgs[0].content + msgs[1].content
    assert "JSON" in blob
    assert "answer_text" in blob  # 参考答案（评分依据）
    assert "source_text" in blob  # 来源锚定
    assert "options" not in blob  # 填空题无选项
    assert "fill_blank" in blob  # 明确填空题型
    assert "光合作用" in msgs[1].content
    assert _section().content in msgs[1].content


def test_step2_fill_blank_prompt_constrains_difficulty_range():
    """子系统2：填空 prompt 同样约束 difficulty_range（含"只能取" + 指定值）。"""
    from quizcraft.services.quiz.prompts import build_step2_fill_blank_messages

    concept = SimpleNamespace(name="光合作用", description="")
    msgs = build_step2_fill_blank_messages(concept, _section(), n=2, difficulty_range=["easy", "medium"])
    blob = msgs[0].content + msgs[1].content
    assert "easy" in blob
    assert "medium" in blob
    assert "只能取" in blob


def test_feedback_prompt_handles_fill_blank_empty_options():
    """子系统2：填空题反馈 prompt 兼容空 options（无选项下标），并嵌入参考答案供反馈溯源。"""
    from quizcraft.services.quiz.prompts import build_feedback_messages

    question = SimpleNamespace(
        stem="光反应发生在____上。",
        options=[],
        correct_option_index=None,
        answer_text="类囊体膜",
        explanation="光反应在类囊体膜",
        source_span={"text": "光反应发生在类囊体膜上。", "page": 12, "section_path": "第2章"},
    )
    msgs = build_feedback_messages(question, selected_option_index=-1, is_correct=False)
    assert len(msgs) == 2
    # 空选项不报错，且参考答案嵌入反馈依据
    assert "类囊体膜" in msgs[1].content
    assert "光反应发生在____上。" in msgs[1].content
