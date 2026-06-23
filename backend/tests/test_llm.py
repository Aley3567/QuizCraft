"""LLM 抽象层测试：Protocol 契约、Mock 注入预设响应、工厂按 provider 路由。"""
import pytest

from quizcraft.config import Settings
from quizcraft.services.llm import (
    LLMClient,
    Message,
    MockLLMClient,
    OpenAICompatibleClient,
    make_llm_client,
)


async def test_mock_llm_returns_preset_response():
    """MockLLMClient 注入预设响应，complete 返回该响应。"""
    client = MockLLMClient(responses=["光合作用的概念是..."])
    resp = await client.complete([Message(role="user", content="解释光合作用")])
    assert resp.content == "光合作用的概念是..."


async def test_mock_llm_rotates_responses():
    """多次调用依次返回队列中的响应，最后一条重复返回。"""
    client = MockLLMClient(responses=["第一句", "第二句"])
    r1 = await client.complete([Message(role="user", content="a")])
    r2 = await client.complete([Message(role="user", content="b")])
    r3 = await client.complete([Message(role="user", content="c")])
    assert r1.content == "第一句"
    assert r2.content == "第二句"
    assert r3.content == "第二句"  # 队列耗尽后停在最后


def test_mock_llm_satisfies_protocol():
    """MockLLMClient 满足 LLMClient Protocol。"""
    client: LLMClient = MockLLMClient(responses=["x"])
    assert isinstance(client, MockLLMClient)


async def test_make_llm_client_defaults_to_mock(settings):
    """无 LLM 配置时默认返回 mock，测试不依赖真实 key。"""
    client = make_llm_client(settings)
    assert isinstance(client, MockLLMClient)


async def test_make_llm_client_openai_when_configured(monkeypatch):
    """provider=openai 且配置了 key/model 时返回 OpenAICompatibleClient。

    清掉测试环境的代理变量：openai SDK 构造 AsyncOpenAI 时会创建 httpx client，
    本机若有 SOCKS 代理且未装 socksio 会在构造阶段报错——这是环境副作用，与被测逻辑无关。
    """
    for var in ("ALL_PROXY", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "http_proxy", "https_proxy"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(
        llm_provider="openai",
        llm_api_key="sk-test",
        llm_model="gpt-4o",
    )
    client = make_llm_client(settings)
    assert isinstance(client, OpenAICompatibleClient)


async def test_make_llm_client_openai_requires_api_key():
    """provider=openai 但缺 key 时抛错——配置不完整应显式失败。"""
    settings = Settings(llm_provider="openai", llm_model="gpt-4o")
    with pytest.raises(ValueError, match="api_key"):
        make_llm_client(settings)


async def test_make_llm_client_unknown_provider_raises():
    settings = Settings(llm_provider="totally-unknown")
    with pytest.raises(ValueError, match="provider"):
        make_llm_client(settings)
