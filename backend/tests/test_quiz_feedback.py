"""答题反馈纯逻辑测试：prompt 构建 + LLM 生成 + 空响应兜底。

不碰 DB / 不走 HTTP，聚焦反馈生成契约。duck-typed question 用 SimpleNamespace。
"""
from types import SimpleNamespace

from quizcraft.services.llm.mock import MockLLMClient
from quizcraft.services.quiz.feedback import _fallback_feedback, generate_feedback
from quizcraft.services.quiz.prompts import build_feedback_messages


def _question(**over) -> SimpleNamespace:
    """最小可用选择题对象（feedback 函数只依赖 options/correct/explanation/source_span）。"""
    base = dict(
        stem="光反应发生在？",
        options=["细胞核", "类囊体膜", "细胞壁", "液泡"],
        correct_option_index=1,
        explanation="光反应在类囊体膜",
        source_span={
            "page": 12,
            "section_path": "第2章 光合作用",
            "text": "光反应发生在类囊体膜上。",
        },
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_build_feedback_messages_contains_verdict_page_and_source():
    """反馈 prompt 必须把学生选择、判定、页码、原文片段都喂给 LLM。"""
    q = _question()
    msgs = build_feedback_messages(q, selected_option_index=0, is_correct=False)
    blob = msgs[0].content + msgs[1].content
    assert "12" in blob  # 课件页码
    assert "类囊体膜上" in blob  # 课件原文片段
    assert "0" in blob  # 学生选择下标
    assert "错误" in blob  # 判定词（错误分支）


async def test_generate_feedback_uses_llm_content():
    """LLM 返回非空文本 → 直接采用（去首尾空白）。"""
    q = _question()
    mock = MockLLMClient()
    expected = "你的课件第12页提到：光反应发生在类囊体膜上，所以选B。"
    mock.set_responses([expected])

    fb = await generate_feedback(q, selected_option_index=1, is_correct=True, llm=mock)

    assert fb == expected
    assert len(mock.calls) == 1


async def test_generate_feedback_falls_back_when_llm_empty():
    """LLM 返回空字符串 → 退化到兜底，兜底仍含页码与正确答案。"""
    q = _question()
    mock = MockLLMClient()
    mock.set_responses(["   "])  # 仅空白

    fb = await generate_feedback(q, selected_option_index=0, is_correct=False, llm=mock)

    assert "12" in fb  # 兜底仍锚定页码
    assert "类囊体膜" in fb  # 引用正确答案文本


def test_fallback_feedback_correct_branch():
    """答对兜底：含「正确」+ 页码 + 正确答案文本。"""
    q = _question()
    fb = _fallback_feedback(q, is_correct=True)
    assert "正确" in fb
    assert "12" in fb
    assert "类囊体膜" in fb  # options[correct]=「类囊体膜」


def test_fallback_feedback_wrong_branch():
    """答错兜底：含「错误」+ 页码 + 正确答案文本。"""
    q = _question()
    fb = _fallback_feedback(q, is_correct=False)
    assert "错误" in fb
    assert "12" in fb
    assert "类囊体膜" in fb


def test_fallback_feedback_handles_missing_source_span():
    """source_span 缺失时不报错，给出不含页码的兜底。"""
    q = _question(source_span={})
    fb = _fallback_feedback(q, is_correct=False)
    assert "错误" in fb
