"""出题引擎：两步生成法 + 简化自评管线。

两步生成法（对齐 DESIGN_DECISIONS 4.2）：
- Step1：LLM 从每个文档分块提取 Concepts，带 source_span（{page, section_path, text}）
- Step2：LLM 对每个 Concept 生成选择题（Bloom 记忆/理解层），每题带 source_span 引用原文
- 简化自评：LLM 对每道题评 accuracy + source-grounding，平均分低于阈值的题被淘汰
  （完整 6 维度 + 可配阈值延后到切片 1.2）

纯逻辑，不碰 DB：输入文档分块 + LLM client，输出结构化 Concepts/Questions。
落库与 source_span 之外的 section/concept 外键关联由 router 负责——
GeneratedConcept.section_index / GeneratedQuestion.section_index / concept_index
保留在输入 sections / 生成 concepts 列表中的位置，供 router 建外键。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from quizcraft.services.llm import LLMClient
from quizcraft.services.quiz.prompts import (
    build_eval_messages,
    build_step1_messages,
    build_step2_messages,
)


class DocumentSection(Protocol):
    """文档分块契约：generator 只需 content/section_path/page_number。"""

    content: str
    section_path: str
    page_number: int


@dataclass
class GeneratedConcept:
    """Step1 产物：从分块提取的概念。

    section_index 指向输入 sections 列表位置，落库时据此取 section.id 建外键。
    """

    section_index: int
    name: str
    description: str | None
    bloom_level: str | None
    source_span: dict  # {page, section_path, text}


@dataclass
class GeneratedQuestion:
    """Step2 产物：带 source_span 的选择题。

    section_index / concept_index 指向输入 sections / 生成 concepts 列表位置，
    落库时据此建外键；concept_name 用于校验关联。
    """

    section_index: int
    concept_index: int
    concept_name: str | None
    stem: str
    options: list[str]
    correct_option_index: int
    explanation: str | None
    bloom_level: str | None
    difficulty: str | None
    source_span: dict  # {page, section_path, text}
    self_eval_score: float | None = None


@dataclass
class QuizGenerationResult:
    concepts: list[GeneratedConcept]
    questions: list[GeneratedQuestion]
    dropped_count: int = 0  # 自评淘汰数
    filtered_count: int = 0  # 子系统2：难度范围过滤掉的题数


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(content: str) -> dict:
    """从 LLM 返回中提取首个 JSON 对象，容错 markdown fence 与前后噪声。

    解析失败抛 ValueError，由调用方捕获后跳过该次 LLM 输出，不中断整体流程。
    """
    text = (content or "").strip()
    if not text:
        raise ValueError("LLM 返回为空")
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM 返回中未找到 JSON 对象")
    return json.loads(text[start : end + 1])


def _build_source_span(section: DocumentSection, source_text: str | None) -> dict:
    """用分块元数据 + LLM 返回的原文片段组装 source_span。"""
    return {
        "page": section.page_number,
        "section_path": section.section_path,
        "text": source_text or "",
    }


def filter_sections_by_scope(sections, chapter_scope: list[str] | None) -> list:
    """按 section_path 子串白名单过滤分块（子系统2 chapter_scope）。

    chapter_scope 为 None 或空列表 → 全部保留（不限章节）。
    否则只保留 section_path 包含任一关键词的分块（子串匹配，如 "第2章" 命中 "第2章 光合作用"）。
    duck-typed：Section ORM 与 SectionData 均有 section_path 属性。
    """
    if not chapter_scope:
        return list(sections)
    return [s for s in sections if any(kw in s.section_path for kw in chapter_scope)]


async def generate_quiz(
    sections: list[DocumentSection],
    llm: LLMClient,
    *,
    concepts_per_section: int = 5,
    questions_per_concept: int = 2,
    self_eval_threshold: float | None = 0.6,
    number: int | None = None,
    difficulty_range: list[str] | None = None,
    question_types: list[str] | None = None,
    bloom_distribution: dict[str, float] | None = None,
) -> QuizGenerationResult:
    """两步生成 + 可选自评 + 子系统2 出题参数控制。

    - self_eval_threshold=None：跳过自评，保留全部生成的题（self_eval_score=None）。
    - 否则对每道题调 LLM 自评，平均分 < 阈值的题被淘汰，dropped_count 计数。
    - LLM 输出解析失败时跳过对应分块/概念/题目，不中断整体流程。
    - 自评解析失败时保守保留题目（不打分），避免因自评抖动丢弃已生成内容。
    - 子系统2 参数：
      - number：目标题数，自评后截断保留高分题（None 不限）。
      - difficulty_range：允许的难度集合，自评前剔除不在范围的题（filtered_count 计数）。
      - question_types / bloom_distribution：透传 prompt 约束 LLM（题型生成当前仅 multiple_choice）。
    """
    # Step1：逐分块提取概念
    concepts: list[GeneratedConcept] = []
    for idx, section in enumerate(sections):
        resp = await llm.complete(
            build_step1_messages(
                section, n=concepts_per_section, bloom_distribution=bloom_distribution
            )
        )
        try:
            data = _extract_json(resp.content)
        except (ValueError, json.JSONDecodeError):
            continue
        for c in data.get("concepts", []):
            try:
                concepts.append(
                    GeneratedConcept(
                        section_index=idx,
                        name=c["name"],
                        description=c.get("description"),
                        bloom_level=c.get("bloom_level"),
                        source_span=_build_source_span(section, c.get("source_text")),
                    )
                )
            except (KeyError, TypeError):
                continue

    # Step2：逐概念生成选择题
    raw_questions: list[GeneratedQuestion] = []
    for ci, concept in enumerate(concepts):
        section = sections[concept.section_index]
        resp = await llm.complete(
            build_step2_messages(
                concept,
                section,
                n=questions_per_concept,
                difficulty_range=difficulty_range,
                question_types=question_types,
                bloom_distribution=bloom_distribution,
            )
        )
        try:
            data = _extract_json(resp.content)
        except (ValueError, json.JSONDecodeError):
            continue
        for q in data.get("questions", []):
            try:
                raw_questions.append(
                    GeneratedQuestion(
                        section_index=concept.section_index,
                        concept_index=ci,
                        concept_name=concept.name,
                        stem=q["stem"],
                        options=q["options"],
                        correct_option_index=q["correct_option_index"],
                        explanation=q.get("explanation"),
                        bloom_level=q.get("bloom_level"),
                        difficulty=q.get("difficulty"),
                        source_span=_build_source_span(section, q.get("source_text")),
                    )
                )
            except (KeyError, TypeError):
                continue

    # 子系统2：difficulty_range 过滤（自评前剔除，避免对不要的题浪费 LLM 自评调用）
    filtered_count = 0
    if difficulty_range:
        allowed = {d.lower() for d in difficulty_range}
        kept_after_diff: list[GeneratedQuestion] = []
        for question in raw_questions:
            if question.difficulty and question.difficulty.lower() in allowed:
                kept_after_diff.append(question)
            else:
                filtered_count += 1
        candidates = kept_after_diff
    else:
        candidates = raw_questions

    # Step3：简化自评（可选）
    kept: list[GeneratedQuestion] = []
    dropped = 0
    if self_eval_threshold is None:
        kept = list(candidates)
    else:
        for question in candidates:
            section = sections[question.section_index]
            resp = await llm.complete(
                build_eval_messages(question, section_content=section.content)
            )
            try:
                data = _extract_json(resp.content)
                score = (float(data["accuracy"]) + float(data["source_grounding"])) / 2
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                question.self_eval_score = None
                kept.append(question)
                continue
            if score < self_eval_threshold:
                dropped += 1
                continue
            question.self_eval_score = score
            kept.append(question)

    # 子系统2：number 截断（自评后截断，保留高分题）
    if number is not None and len(kept) > number:
        kept = kept[:number]

    return QuizGenerationResult(
        concepts=concepts, questions=kept, dropped_count=dropped, filtered_count=filtered_count
    )
