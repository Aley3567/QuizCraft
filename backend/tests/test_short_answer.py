"""简答评分服务测试：Mock LLM，验证 rubric 评分 0-1 + 引用文档反馈 + 兜底降级。

纯逻辑测试，不碰 DB——输入 duck-typed question（{stem, answer_text, source_span}）+ MockLLMClient。
"""
import pytest
from types import SimpleNamespace

from quizcraft.services.llm import MockLLMClient
from quizcraft.services.quiz.short_answer import ShortAnswerScore, score_short_answer

QUESTION = SimpleNamespace(
    stem="简述光反应的发生部位。",
    answer_text="光反应发生在类囊体膜上，负责水的光解与 ATP/NADPH 的生成。",
    source_span={"text": "光反应发生在类囊体膜上。", "page": 12, "section_path": "第2章 光合作用"},
)


async def test_score_returns_score_and_source_grounded_feedback():
    """LLM 返回 {score, feedback} → 解析出分数与引用原文的反馈。"""
    llm = MockLLMClient(
        responses=['{"score": 0.8, "feedback": "你的课件第12页提到光反应发生在类囊体膜上。"}']
    )
    r = await score_short_answer(QUESTION, student_answer="在类囊体膜上", llm=llm)
    assert isinstance(r, ShortAnswerScore)
    assert r.score == pytest.approx(0.8)
    assert "类囊体膜" in r.feedback


async def test_score_falls_back_on_empty_response():
    """LLM 空响应 → 兜底 score=0 + 锚定页码的反馈（不阻塞作答流程）。"""
    llm = MockLLMClient(responses=[""])
    r = await score_short_answer(QUESTION, student_answer="在细胞核里", llm=llm)
    assert r.score == 0.0
    assert "12" in r.feedback  # 兜底锚定页码


async def test_score_falls_back_on_invalid_json():
    """LLM 返回非 JSON → 兜底 score=0。"""
    llm = MockLLMClient(responses=["这不是 JSON"])
    r = await score_short_answer(QUESTION, student_answer="随便", llm=llm)
    assert r.score == 0.0


async def test_score_clamps_above_one():
    """LLM 返回 score>1 → clamp 到 1.0。"""
    llm = MockLLMClient(responses=['{"score": 1.5, "feedback": "完美"}'])
    r = await score_short_answer(QUESTION, student_answer="好", llm=llm)
    assert r.score == 1.0


async def test_score_clamps_below_zero():
    """LLM 返回 score<0 → clamp 到 0.0。"""
    llm = MockLLMClient(responses=['{"score": -0.3, "feedback": "错"}'])
    r = await score_short_answer(QUESTION, student_answer="差", llm=llm)
    assert r.score == 0.0


async def test_score_falls_back_when_feedback_missing():
    """LLM 返回 score 但无 feedback → 走兜底（反馈必须非空且锚定来源）。"""
    llm = MockLLMClient(responses=['{"score": 0.7}'])
    r = await score_short_answer(QUESTION, student_answer="x", llm=llm)
    assert r.score == 0.0  # 无有效 feedback → 整体降级兜底
    assert "12" in r.feedback
