"""答题反馈生成：据学生作答 + source_span，用 LLM 生成引用文档原文的解释。

对齐 DESIGN_DECISIONS 4.3：错题/对题反馈必须引用用户文档具体段落（页码 + 章节路径 + 原文片段），
而非通用解析。LLM 返回为空或调用异常时，退化到确定性兜底文本（仍锚定来源）——判分不依赖 LLM。

纯逻辑，不碰 DB：输入 duck-typed question（{options, correct_option_index, explanation, source_span}）
+ LLM client，返回反馈文本。落库由 router 负责。
"""
from __future__ import annotations

from quizcraft.services.llm import LLMClient
from quizcraft.services.quiz.prompts import build_feedback_messages


async def generate_feedback(
    question,
    *,
    selected_option_index: int,
    is_correct: bool,
    llm: LLMClient,
) -> str:
    """调 LLM 生成引用原文的反馈；空响应或异常时走确定性兜底。

    LLM 失败不得阻塞判分与作答流程，故宽异常捕获后退化兜底（真实部署的 LLM 网络抖动可恢复）。
    """
    try:
        resp = await llm.complete(
            build_feedback_messages(
                question,
                selected_option_index=selected_option_index,
                is_correct=is_correct,
            )
        )
        content = (resp.content or "").strip()
        if content:
            return content
    except Exception:  # noqa: BLE001  LLM 调用失败不应阻塞作答，退化兜底
        pass
    return _fallback_feedback(question, is_correct=is_correct)


def _fallback_feedback(question, *, is_correct: bool) -> str:
    """确定性兜底反馈：含判定、正确答案、来源页码/章节/原文片段。"""
    span = getattr(question, "source_span", None) or {}
    page = span.get("page")
    section_path = span.get("section_path", "")
    text = span.get("text", "")
    options = getattr(question, "options", None) or []
    correct_idx = getattr(question, "correct_option_index", None)
    correct_text = (
        options[correct_idx]
        if correct_idx is not None and 0 <= correct_idx < len(options)
        else ""
    )

    verdict = "回答正确。" if is_correct else "回答错误。"
    correct_line = f"正确答案：「{correct_text}」。" if correct_text else ""
    ref = f"参考课件第{page}页" if page is not None else "参考课件"
    if section_path:
        ref += f"（{section_path}）"
    ref += "。"
    source_line = f"原文：{text}" if text else ""
    return " ".join(part for part in (verdict, correct_line, ref, source_line) if part)
