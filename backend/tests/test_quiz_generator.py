"""出题引擎两步生成 + 简化自评测试：Mock LLM，验证 Concepts/Questions 提取、source_span 溯源、自评淘汰。

纯逻辑测试，不碰 DB——输入 SectionData + MockLLMClient，输出结构化结果。
"""
import pytest

from quizcraft.services.llm import MockLLMClient
from quizcraft.services.parsing import SectionData
from quizcraft.services.quiz import generate_quiz


SECTION = SectionData(
    section_path="第2章 光合作用",
    page_number=12,
    content="光合作用是植物利用光能合成有机物的过程。光反应发生在类囊体膜上，暗反应在基质中。",
    token_count=30,
    order_index=0,
)

STEP1_JSON = (
    '{"concepts": [{"name": "光合作用", "description": "植物利用光能合成有机物", '
    '"bloom_level": "记忆", "source_text": "光合作用是植物利用光能合成有机物的过程。"}]}'
)

STEP2_JSON = (
    '{"questions": [{"stem": "光合作用的光反应主要发生在？", '
    '"options": ["细胞核", "类囊体膜", "细胞壁", "液泡"], "correct_option_index": 1, '
    '"explanation": "光反应发生在类囊体膜上。", "bloom_level": "记忆", "difficulty": "easy", '
    '"source_text": "光反应发生在类囊体膜上。"}]}'
)

EVAL_HIGH = '{"accuracy": 0.9, "source_grounding": 0.9}'
EVAL_LOW = '{"accuracy": 0.2, "source_grounding": 0.3}'


async def test_step1_extracts_concepts_with_source_span():
    """Step1：LLM 返回 concepts JSON，generator 提取概念并补全 source_span（page/section_path/text）。"""
    result = await generate_quiz(
        [SECTION], MockLLMClient(responses=[STEP1_JSON, STEP2_JSON]), self_eval_threshold=None
    )
    assert len(result.concepts) == 1
    c = result.concepts[0]
    assert c.name == "光合作用"
    assert c.bloom_level == "记忆"
    assert c.source_span["page"] == 12
    assert c.source_span["section_path"] == "第2章 光合作用"
    assert c.source_span["text"] == "光合作用是植物利用光能合成有机物的过程。"


async def test_step2_generates_questions_with_source_span():
    """Step2：LLM 返回 questions JSON，generator 生成选择题并补全 source_span，关联回 concept。"""
    result = await generate_quiz(
        [SECTION], MockLLMClient(responses=[STEP1_JSON, STEP2_JSON]), self_eval_threshold=None
    )
    assert len(result.questions) == 1
    q = result.questions[0]
    assert q.stem == "光合作用的光反应主要发生在？"
    assert q.options == ["细胞核", "类囊体膜", "细胞壁", "液泡"]
    assert q.correct_option_index == 1
    assert q.source_span["page"] == 12
    assert q.source_span["text"] == "光反应发生在类囊体膜上。"
    assert q.concept_name == "光合作用"
    assert q.self_eval_score is None  # 跳过自评时不打分
    assert result.dropped_count == 0


async def test_self_eval_drops_below_threshold():
    """自评平均分 < 阈值 → 题目被淘汰，dropped_count 计数。"""
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, STEP2_JSON, EVAL_LOW]),
        self_eval_threshold=0.6,
    )
    assert len(result.questions) == 0
    assert result.dropped_count == 1


async def test_self_eval_keeps_at_or_above_threshold():
    """自评平均分 >= 阈值 → 保留题目并记录 self_eval_score。"""
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, STEP2_JSON, EVAL_HIGH]),
        self_eval_threshold=0.6,
    )
    assert len(result.questions) == 1
    assert result.questions[0].self_eval_score == pytest.approx(0.9)


async def test_invalid_llm_output_skipped():
    """LLM 返回非 JSON → 跳过该分块，不中断整体流程。"""
    result = await generate_quiz(
        [SECTION], MockLLMClient(responses=["这不是 JSON", STEP2_JSON]), self_eval_threshold=None
    )
    assert len(result.concepts) == 0
    assert len(result.questions) == 0


async def test_markdown_fenced_json_extracted():
    """LLM 返回 ```json ... ``` 包裹的 JSON → 正确剥离 fence 后解析。"""
    fenced = "```json\n" + STEP1_JSON + "\n```"
    result = await generate_quiz(
        [SECTION], MockLLMClient(responses=[fenced, STEP2_JSON]), self_eval_threshold=None
    )
    assert len(result.concepts) == 1


async def test_multi_section_source_spans_distinct():
    """多分块：concept/question 的 source_span 按各自所属分块正确归属（page 不同）。"""
    s1 = SectionData(section_path="第1章", page_number=1, content="内容一", token_count=5, order_index=0)
    s2 = SectionData(section_path="第2章", page_number=5, content="内容二", token_count=5, order_index=1)
    step1_a = (
        '{"concepts": [{"name": "概念A", "description": "", "bloom_level": "记忆", '
        '"source_text": "内容一"}]}'
    )
    step1_b = (
        '{"concepts": [{"name": "概念B", "description": "", "bloom_level": "理解", '
        '"source_text": "内容二"}]}'
    )
    step2_a = (
        '{"questions": [{"stem": "题A", "options": ["x", "y", "z", "w"], '
        '"correct_option_index": 0, "explanation": "", "bloom_level": "记忆", '
        '"difficulty": "easy", "source_text": "内容一"}]}'
    )
    step2_b = (
        '{"questions": [{"stem": "题B", "options": ["x", "y", "z", "w"], '
        '"correct_option_index": 0, "explanation": "", "bloom_level": "理解", '
        '"difficulty": "medium", "source_text": "内容二"}]}'
    )
    mock = MockLLMClient(responses=[step1_a, step1_b, step2_a, step2_b])
    result = await generate_quiz([s1, s2], mock, self_eval_threshold=None)

    assert len(result.concepts) == 2
    by_name = {c.name: c for c in result.concepts}
    assert by_name["概念A"].source_span["page"] == 1
    assert by_name["概念B"].source_span["page"] == 5

    assert len(result.questions) == 2
    q_by_stem = {q.stem: q for q in result.questions}
    assert q_by_stem["题A"].source_span["page"] == 1
    assert q_by_stem["题B"].source_span["page"] == 5


async def test_empty_sections_returns_empty():
    """无分块 → 空结果，不调用 LLM。"""
    result = await generate_quiz([], MockLLMClient(), self_eval_threshold=None)
    assert result.concepts == []
    assert result.questions == []


async def test_difficulty_filter_drops_unwanted_difficulty():
    """子系统2：difficulty_range 过滤掉不在范围内的题，filtered_count 计数。"""
    step2_medium = (
        '{"questions": [{"stem": "题", "options": ["a", "b", "c", "d"], '
        '"correct_option_index": 0, "explanation": "", "bloom_level": "记忆", '
        '"difficulty": "medium", "source_text": "光反应发生在类囊体膜上。"}]}'
    )
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, step2_medium]),
        self_eval_threshold=None,
        difficulty_range=["easy"],
    )
    assert len(result.questions) == 0
    assert result.filtered_count == 1


async def test_number_truncates_to_target():
    """子系统2：number 截断生成题数到目标值（自评后截断，保留高分题）。"""
    step2_two = (
        '{"questions": ['
        '{"stem": "题1", "options": ["a", "b", "c", "d"], "correct_option_index": 0, '
        '"explanation": "", "bloom_level": "记忆", "difficulty": "easy", '
        '"source_text": "光反应发生在类囊体膜上。"}, '
        '{"stem": "题2", "options": ["a", "b", "c", "d"], "correct_option_index": 0, '
        '"explanation": "", "bloom_level": "理解", "difficulty": "easy", '
        '"source_text": "光反应发生在类囊体膜上。"}'
        "]}"
    )
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, step2_two]),
        self_eval_threshold=None,
        number=1,
    )
    assert len(result.questions) == 1


def test_filter_sections_by_scope_substring_match():
    """子系统2：chapter_scope 按 section_path 子串白名单过滤分块；None/空=全部保留。"""
    from quizcraft.services.quiz.generator import filter_sections_by_scope

    s1 = SectionData(section_path="第1章 绪论", page_number=1, content="x", token_count=5, order_index=0)
    s2 = SectionData(section_path="第2章 光合作用", page_number=5, content="y", token_count=5, order_index=1)
    s3 = SectionData(section_path="第3章 呼吸作用", page_number=9, content="z", token_count=5, order_index=2)
    kept = filter_sections_by_scope([s1, s2, s3], ["第2章"])
    assert [s.section_path for s in kept] == ["第2章 光合作用"]
    assert len(filter_sections_by_scope([s1, s2], None)) == 2
    assert len(filter_sections_by_scope([s1, s2], [])) == 2


def test_filter_sections_by_scope_multiple_keywords():
    """子系统2：多个章节关键词任一匹配即纳入。"""
    from quizcraft.services.quiz.generator import filter_sections_by_scope

    s1 = SectionData(section_path="第1章 绪论", page_number=1, content="x", token_count=5, order_index=0)
    s2 = SectionData(section_path="第2章 光合作用", page_number=5, content="y", token_count=5, order_index=1)
    s3 = SectionData(section_path="第3章 呼吸作用", page_number=9, content="z", token_count=5, order_index=2)
    kept = filter_sections_by_scope([s1, s2, s3], ["第1章", "第3章"])
    assert [s.section_path for s in kept] == ["第1章 绪论", "第3章 呼吸作用"]


STEP2_SHORT_JSON = (
    '{"questions": [{"stem": "简述光反应的发生部位。", '
    '"answer_text": "光反应发生在类囊体膜上，负责水的光解。", "explanation": "考察光反应部位。", '
    '"bloom_level": "理解", "difficulty": "medium", "source_text": "光反应发生在类囊体膜上。"}]}'
)


async def test_step2_generates_short_answer_question():
    """子系统3：question_types=['short_answer'] → 生成简答题，无 options/correct_option_index，带 answer_text。"""
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, STEP2_SHORT_JSON]),
        self_eval_threshold=None,
        question_types=["short_answer"],
    )
    assert len(result.questions) == 1
    q = result.questions[0]
    assert q.question_type == "short_answer"
    assert q.stem == "简述光反应的发生部位。"
    assert q.answer_text == "光反应发生在类囊体膜上，负责水的光解。"
    assert q.correct_option_index is None
    assert q.options == []
    assert q.source_span["text"] == "光反应发生在类囊体膜上。"
    assert q.source_span["page"] == 12


async def test_mixed_question_types_generates_both_types():
    """子系统3：question_types=['multiple_choice','short_answer'] → 每概念生成一道选择 + 一道简答。"""
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, STEP2_JSON, STEP2_SHORT_JSON]),
        self_eval_threshold=None,
        questions_per_concept=1,
        question_types=["multiple_choice", "short_answer"],
    )
    assert len(result.questions) == 2
    types = {q.question_type for q in result.questions}
    assert types == {"multiple_choice", "short_answer"}
    sa = next(q for q in result.questions if q.question_type == "short_answer")
    assert sa.answer_text is not None
    mc = next(q for q in result.questions if q.question_type == "multiple_choice")
    assert mc.correct_option_index == 1
    assert mc.options == ["细胞核", "类囊体膜", "细胞壁", "液泡"]


async def test_short_answer_skips_self_eval():
    """子系统3：简答题跳过生成期自评（评分在答题时由 LLM rubric 完成），self_eval_score=None。"""
    # 仅 3 次 LLM 调用：step1 + step2 简答（无自评调用），验证不耗第 4 次响应
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, STEP2_SHORT_JSON]),
        self_eval_threshold=0.6,
        question_types=["short_answer"],
    )
    assert len(result.questions) == 1
    assert result.questions[0].self_eval_score is None
    assert result.dropped_count == 0  # 简答题不因自评被淘汰


async def test_short_answer_respects_difficulty_range():
    """子系统3：difficulty_range 同样过滤简答题（简答题也带 difficulty 字段）。"""
    step2_hard = (
        '{"questions": [{"stem": "题", "answer_text": "答", "explanation": "", '
        '"bloom_level": "应用", "difficulty": "hard", "source_text": "光反应发生在类囊体膜上。"}]}'
    )
    result = await generate_quiz(
        [SECTION],
        MockLLMClient(responses=[STEP1_JSON, step2_hard]),
        self_eval_threshold=None,
        question_types=["short_answer"],
        difficulty_range=["easy"],
    )
    assert len(result.questions) == 0
    assert result.filtered_count == 1
