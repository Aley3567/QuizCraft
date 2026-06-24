"""出题引擎 prompt 构建：两步生成法（Step1 提取概念 / Step2 生成选择题）+ 简化自评。

对齐 DESIGN_DECISIONS 4.2：
- 来源锚定：每题/每概念必须引用文档原文 source_text，供错题反馈溯源
- 错误选项基于常见误解，不是随机错误
- 完整 6 维自我批评（子系统6）：评 accuracy/clarity/difficulty/source-grounding/non-trivial/non-ambiguous

要求 LLM 严格只返回 JSON，由 generator 解析容错（markdown fence / 前后噪声）。

prompt 函数只需 duck-typed 对象，不依赖 ORM：
- section: {content, section_path, page_number}
- concept: {name, description}
- question: {stem, options, correct_option_index, explanation, source_span}
"""
from __future__ import annotations

from quizcraft.services.llm.base import Message


def _fmt_list(items: list[str]) -> str:
    """把 ['easy','medium'] 格式化为 '"easy" 或 "medium"'，用于 prompt 枚举列举。"""
    return " 或 ".join(f'"{i}"' for i in items)


def _fmt_dist(dist: dict[str, float]) -> str:
    """把 {'记忆':0.4,...} 格式化为 '记忆 40%、理解 30%...'，用于 prompt 分布约束。"""
    return "、".join(f"{k} {int(round(v * 100))}%" for k, v in dist.items())


def build_step1_messages(section, *, n: int = 5, bloom_distribution: dict | None = None) -> list[Message]:
    """Step1：从文档分块提取 n 个核心学习概念，每个带文档原文 source_text。

    子系统2：Bloom 扩展到完整四层（记忆/理解/应用/分析）；可选 bloom_distribution 约束概念层级分布。
    """
    bloom_clause = (
        f"概念层级分布应大致符合：{_fmt_dist(bloom_distribution)}。\n"
        if bloom_distribution
        else ""
    )
    system = (
        "你是学习材料分析专家。从给定的文档片段中提取核心学习概念（定义、关键术语、重要原理）。\n"
        f"提取 {n} 个左右核心概念，每个概念必须附带文档中的原文片段用于溯源。\n"
        'bloom_level 只能取 "记忆"、"理解"、"应用" 或 "分析"。\n'
        + bloom_clause
        + "严格只返回 JSON，不要输出任何解释或额外文字，格式：\n"
        '{"concepts": [{"name": "概念名", "description": "简短描述", '
        '"bloom_level": "记忆", "source_text": "文档中的原文片段"}]}'
    )
    user = (
        f"文档片段（章节：{section.section_path}，页码：{section.page_number}）：\n"
        f"{section.content}"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]


def build_step2_messages(
    concept,
    section,
    *,
    n: int = 2,
    difficulty_range: list[str] | None = None,
    question_types: list[str] | None = None,
    bloom_distribution: dict | None = None,
) -> list[Message]:
    """Step2：基于概念 + 文档原文生成 n 道单选题，干扰项基于常见误解，每题带 source_text。

    子系统2 出题参数控制：
    - difficulty_range：约束难度取值（prompt 显式列举允许难度，其余禁用）
    - question_types：题型约束（当前仅 multiple_choice；其他题型生成留后续子系统配套评分方式）
    - bloom_distribution：题目 Bloom 分布比例
    - Bloom 完整四层（记忆/理解/应用/分析），并要求 explanation 开头简述为何定为该层级
    """
    diff_clause = (
        f"difficulty 只能取 {_fmt_list(difficulty_range)}（不得取其他难度）。\n"
        if difficulty_range
        else 'difficulty 取 "easy"、"medium" 或 "hard"。\n'
    )
    qt_clause = f"题型限定：{_fmt_list(question_types)}。\n" if question_types else ""
    bloom_dist_clause = (
        f"题目 Bloom 层级分布应大致符合：{_fmt_dist(bloom_distribution)}；\n"
        if bloom_distribution
        else ""
    )
    system = (
        "你是出题专家。基于给定概念和文档原文，生成单选题。\n"
        f"生成 {n} 道题，每题恰好 4 个选项，干扰项要基于常见误解而不是随机错误。\n"
        + qt_clause
        + diff_clause
        + bloom_dist_clause
        + 'bloom_level 取 "记忆"、"理解"、"应用" 或 "分析"，并在 explanation 开头简述为何定为该层级。\n'
        "correct_option_index 是正确答案在 options 中的下标（0-3）。\n"
        "每题必须附带文档原文 source_text（必须来自给定文档片段）。\n"
        "严格只返回 JSON，不要输出任何解释或额外文字，格式：\n"
        '{"questions": [{"stem": "题干", "options": ["选项A", "选项B", "选项C", "选项D"], '
        '"correct_option_index": 0, "explanation": "解析", "bloom_level": "记忆", '
        '"difficulty": "easy", "source_text": "文档原文片段"}]}'
    )
    user = (
        f"概念：{concept.name}\n"
        f"概念描述：{concept.description or ''}\n"
        f"文档原文片段（章节：{section.section_path}，页码：{section.page_number}）：\n"
        f"{section.content}"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]


def build_eval_messages(question, *, section_content: str) -> list[Message]:
    """完整 6 维自评（子系统6）：评估题目质量 6 个维度，各 0-1 浮点。

    维度（对齐 SLICE_PHASE_1.md 切片 1.2 子系统 6）：
    - accuracy：题目答案与解释是否正确无误
    - clarity：题干表述是否清晰易懂
    - difficulty：难度是否与标注 difficulty 一致
    - source_grounding：source_text 是否真来自给定文档原文（题目是否真实锚定文档）
    - non_trivial：题目是否非琐碎送分（有一定区分度）
    - non_ambiguous：题目是否有唯一明确正确答案（无歧义）

    generator 解析时对返回中实际存在的维度取平均（向后兼容旧 2 维响应）。
    difficulty 字段用 getattr 安全访问，兼容不含该属性的 duck-typed question。
    """
    options_text = "\n".join(f"{i}. {o}" for i, o in enumerate(question.options))
    difficulty_label = getattr(question, "difficulty", None) or ""
    system = (
        "你是出题质量审核员。只评估以下 6 个维度（各 0-1 浮点数）：\n"
        "- accuracy：题目答案与解释是否正确无误\n"
        "- clarity：题干表述是否清晰易懂\n"
        "- difficulty：难度是否与标注的 difficulty 一致\n"
        "- source_grounding：source_text 是否真的来自给定文档原文（即题目是否真实锚定文档）\n"
        "- non_trivial：题目是否非琐碎送分（有一定区分度）\n"
        "- non_ambiguous：题目是否有唯一明确正确答案（无歧义）\n"
        "严格只返回 JSON，不要输出任何解释或额外文字，格式：\n"
        '{"accuracy": 0.9, "clarity": 0.8, "difficulty": 0.8, '
        '"source_grounding": 0.9, "non_trivial": 0.7, "non_ambiguous": 0.9}'
    )
    user = (
        f"题干：{question.stem}\n"
        f"选项：\n{options_text}\n"
        f"正确答案下标：{question.correct_option_index}\n"
        f"解析：{question.explanation or ''}\n"
        f"标注难度：{difficulty_label}\n"
        f"题目声称的文档原文：{question.source_span.get('text', '')}\n"
        f"实际文档片段：\n{section_content}"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]


def build_step2_short_answer_messages(
    concept,
    section,
    *,
    n: int = 2,
    difficulty_range: list[str] | None = None,
    bloom_distribution: dict | None = None,
) -> list[Message]:
    """Step2 简答题：基于概念 + 文档原文生成 n 道简答题，每题带参考答案 answer_text 与 source_text。

    子系统3：简答题型生成。answer_text 作为参考答案/rubric，供答题时 LLM 评分依据。
    简答题无 options/correct_option_index（由 generator 置 None）。

    - difficulty_range / bloom_distribution：同选择题的约束语义（透传 prompt）
    - Bloom 完整四层，explanation 开头简述为何定该层级
    """
    diff_clause = (
        f"difficulty 只能取 {_fmt_list(difficulty_range)}（不得取其他难度）。\n"
        if difficulty_range
        else 'difficulty 取 "easy"、"medium" 或 "hard"。\n'
    )
    bloom_dist_clause = (
        f"题目 Bloom 层级分布应大致符合：{_fmt_dist(bloom_distribution)}；\n"
        if bloom_distribution
        else ""
    )
    system = (
        "你是出题专家。基于给定概念和文档原文，生成简答题（short_answer）。\n"
        f"生成 {n} 道题，每题必须提供参考答案 answer_text（作为评分 rubric），"
        "answer_text 必须能从给定文档原文推导出来。\n"
        + diff_clause
        + bloom_dist_clause
        + 'bloom_level 取 "记忆"、"理解"、"应用" 或 "分析"，并在 explanation 开头简述为何定为该层级。\n'
        "每题必须附带文档原文 source_text（必须来自给定文档片段）。\n"
        "严格只返回 JSON，不要输出任何解释或额外文字，格式：\n"
        '{"questions": [{"stem": "题干", "answer_text": "参考答案", '
        '"explanation": "解析", "bloom_level": "记忆", "difficulty": "easy", '
        '"source_text": "文档原文片段"}]}'
    )
    user = (
        f"概念：{concept.name}\n"
        f"概念描述：{concept.description or ''}\n"
        f"文档原文片段（章节：{section.section_path}，页码：{section.page_number}）：\n"
        f"{section.content}"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]


def build_short_answer_eval_messages(
    question, *, student_answer: str, section_content: str
) -> list[Message]:
    """简答评分：以 answer_text 为 rubric，结合学生作答与文档原文，评 0-1 分 + 引用文档解释。

    对齐 DESIGN_DECISIONS 4.3：反馈必须引用文档原文（页码 + 章节 + 原文片段），而非通用解析。
    score 为 0-1 浮点（0=完全错误，1=完全正确）。
    question: {stem, answer_text, source_span}
    """
    span = question.source_span or {}
    page = span.get("page")
    section_path = span.get("section_path", "")
    source_text = span.get("text", "")
    system = (
        "你是学习辅导老师，负责评阅学生简答题。依据题目给定的参考答案作为评分 rubric，"
        "结合学生作答与文档原文，给出 0-1 的浮点分数（0=完全错误，1=完全正确，允许小数）。\n"
        "核心要求：feedback 必须引用文档具体段落（页码 + 章节路径 + 原文片段）解释对错，"
        "而非与课件无关的通用解析。\n"
        "严格只返回 JSON，不要输出任何解释或额外文字，格式：\n"
        '{"score": 0.8, "feedback": "你的课件第12页提到：…原文…，所以…"}'
    )
    user = (
        f"题干：{question.stem}\n"
        f"参考答案（rubric）：{question.answer_text or ''}\n"
        f"学生作答：{student_answer}\n"
        f"课件页码：{page}\n"
        f"章节路径：{section_path}\n"
        f"课件原文片段：{source_text}\n"
        f"实际文档片段：\n{section_content}"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]


def build_feedback_messages(
    question, *, selected_option_index: int, is_correct: bool
) -> list[Message]:
    """答题反馈：据学生作答 + 文档原文，生成引用课件具体段落的解释（非通用解析）。

    对齐 DESIGN_DECISIONS 4.3：错题反馈必须引用用户文档原文（页码 + 章节路径 + 片段）。
    question: {stem, options, correct_option_index, explanation, source_span}
    """
    options_text = "\n".join(f"{i}. {o}" for i, o in enumerate(question.options))
    span = question.source_span or {}
    page = span.get("page")
    section_path = span.get("section_path", "")
    source_text = span.get("text", "")
    verdict = "正确" if is_correct else "错误"
    system = (
        "你是学习辅导老师。根据学生作答情况生成一条简洁的反馈。\n"
        "核心要求：必须引用学生课件的具体段落（页码 + 章节路径 + 原文片段）来解释为什么这是正确答案，"
        "而不是给出与课件无关的通用解析。\n"
        '格式建议：「你的课件第 X 页（章节）提到：…原文…，所以…」。\n'
        "只返回反馈正文纯文本，不要 JSON，不要 markdown 格式，不要前后引号。"
    )
    user = (
        f"题干：{question.stem}\n"
        f"选项：\n{options_text}\n"
        f"学生选择下标：{selected_option_index}（{verdict}）\n"
        f"正确答案下标：{question.correct_option_index}\n"
        f"课件页码：{page}\n"
        f"章节路径：{section_path}\n"
        f"课件原文片段：{source_text}\n"
        f"题目预设解析：{question.explanation or ''}\n"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]
