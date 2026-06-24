"""简答评分服务：LLM 按 rubric（answer_text 参考答案）评 0-1 分 + 引用文档反馈。

对齐 DESIGN_DECISIONS 4.3：反馈必须引用文档原文（页码 + 章节路径 + 原文片段），而非通用解析。
LLM 返回为空、解析失败或调用异常时，退化到确定性兜底（score=0 + 锚定来源的反馈）——
判分依赖 LLM 但失败不阻塞作答流程（真实部署的 LLM 网络抖动可恢复）。

纯逻辑，不碰 DB：输入 duck-typed question（{stem, answer_text, source_span}）+ LLM client，
返回 ShortAnswerScore。落库由 router 负责。
"""
from __future__ import annotations

from dataclasses import dataclass

from quizcraft.services.llm import LLMClient
from quizcraft.services.quiz.generator import _extract_json
from quizcraft.services.quiz.prompts import build_short_answer_eval_messages


@dataclass
class ShortAnswerScore:
    """简答评分结果：0-1 分数 + 引用文档原文的反馈。"""

    score: float
    feedback: str


def _clamp01(value: float) -> float:
    """把分数约束到 [0, 1]。"""
    return max(0.0, min(1.0, value))


async def score_short_answer(
    question,
    *,
    student_answer: str,
    llm: LLMClient,
) -> ShortAnswerScore:
    """调 LLM 按 rubric 评分；空响应/解析失败/缺 feedback 时走确定性兜底。

    section_content 取自 question.source_span.text（答题时已无完整分块，rubric 主要靠
    answer_text + 学生作答 + 原文片段）。
    """
    span = getattr(question, "source_span", None) or {}
    section_content = span.get("text", "")
    try:
        resp = await llm.complete(
            build_short_answer_eval_messages(
                question, student_answer=student_answer, section_content=section_content
            )
        )
        data = _extract_json(resp.content)
        score = _clamp01(float(data["score"]))
        feedback = str(data.get("feedback", "")).strip()
        if feedback:
            return ShortAnswerScore(score=score, feedback=feedback)
    except (ValueError, KeyError, TypeError):  # 解析失败 → 兜底
        pass
    except Exception:  # noqa: BLE001  LLM 调用失败不阻塞作答，退化兜底
        pass
    return _fallback_score(question)


def _fallback_score(question) -> ShortAnswerScore:
    """确定性兜底：score=0 + 锚定页码/章节/原文片段的反馈。"""
    span = getattr(question, "source_span", None) or {}
    page = span.get("page")
    section_path = span.get("section_path", "")
    text = span.get("text", "")
    ref = f"参考课件第{page}页" if page is not None else "参考课件"
    if section_path:
        ref += f"（{section_path}）"
    ref += "。"
    source_line = f"原文：{text}" if text else ""
    feedback = " ".join(
        part for part in ("评分服务暂不可用，无法判分。", ref, source_line) if part
    )
    return ShortAnswerScore(score=0.0, feedback=feedback)
