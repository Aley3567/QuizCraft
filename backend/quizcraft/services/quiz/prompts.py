"""出题引擎 prompt 构建：两步生成法（Step1 提取概念 / Step2 生成选择题）+ 简化自评。

对齐 DESIGN_DECISIONS 4.2：
- 来源锚定：每题/每概念必须引用文档原文 source_text，供错题反馈溯源
- 错误选项基于常见误解，不是随机错误
- 简化自我批评：只评 accuracy + source-grounding（完整 6 维度延后到切片 1.2）

要求 LLM 严格只返回 JSON，由 generator 解析容错（markdown fence / 前后噪声）。

prompt 函数只需 duck-typed 对象，不依赖 ORM：
- section: {content, section_path, page_number}
- concept: {name, description}
- question: {stem, options, correct_option_index, explanation, source_span}
"""
from __future__ import annotations

from quizcraft.services.llm.base import Message


def build_step1_messages(section, *, n: int = 5) -> list[Message]:
    """Step1：从文档分块提取 n 个核心学习概念，每个带文档原文 source_text。"""
    system = (
        "你是学习材料分析专家。从给定的文档片段中提取核心学习概念（定义、关键术语、重要原理）。\n"
        f"提取 {n} 个左右核心概念，每个概念必须附带文档中的原文片段用于溯源。\n"
        'bloom_level 只能取 "记忆" 或 "理解"。\n'
        "严格只返回 JSON，不要输出任何解释或额外文字，格式：\n"
        '{"concepts": [{"name": "概念名", "description": "简短描述", '
        '"bloom_level": "记忆", "source_text": "文档中的原文片段"}]}'
    )
    user = (
        f"文档片段（章节：{section.section_path}，页码：{section.page_number}）：\n"
        f"{section.content}"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]


def build_step2_messages(concept, section, *, n: int = 2) -> list[Message]:
    """Step2：基于概念 + 文档原文生成 n 道单选题，干扰项基于常见误解，每题带 source_text。"""
    system = (
        "你是出题专家。基于给定概念和文档原文，生成单选题。\n"
        f"生成 {n} 道题，每题恰好 4 个选项，干扰项要基于常见误解而不是随机错误。\n"
        "correct_option_index 是正确答案在 options 中的下标（0-3）。\n"
        "每题必须附带文档原文 source_text（必须来自给定文档片段）。\n"
        'bloom_level 取 "记忆" 或 "理解"；difficulty 取 "easy"、"medium" 或 "hard"。\n'
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
    """简化自评：评估题目 accuracy（答案/解释正确性）与 source-grounding（是否真基于文档原文）。"""
    options_text = "\n".join(f"{i}. {o}" for i, o in enumerate(question.options))
    system = (
        "你是出题质量审核员。只评估以下两个维度（各 0-1 浮点数）：\n"
        "- accuracy：题目答案与解释是否正确无误\n"
        "- source_grounding：source_text 是否真的来自给定文档原文（即题目是否真实锚定文档）\n"
        "严格只返回 JSON，不要输出任何解释或额外文字，格式：\n"
        '{"accuracy": 0.9, "source_grounding": 0.8}'
    )
    user = (
        f"题干：{question.stem}\n"
        f"选项：\n{options_text}\n"
        f"正确答案下标：{question.correct_option_index}\n"
        f"解析：{question.explanation or ''}\n"
        f"题目声称的文档原文：{question.source_span.get('text', '')}\n"
        f"实际文档片段：\n{section_content}"
    )
    return [Message(role="system", content=system), Message(role="user", content=user)]
