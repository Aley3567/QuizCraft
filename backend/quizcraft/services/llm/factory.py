"""LLM 客户端工厂：按 Settings.provider 路由到具体实现。"""
from __future__ import annotations

from quizcraft.config import Settings
from quizcraft.services.llm.base import LLMClient
from quizcraft.services.llm.mock import MockLLMClient
from quizcraft.services.llm.openai_compat import OpenAICompatibleClient


def make_llm_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider.lower()

    if provider == "mock":
        return MockLLMClient()

    if provider == "openai":
        if not settings.llm_api_key:
            raise ValueError("provider=openai 需要配置 api_key")
        return OpenAICompatibleClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )

    raise ValueError(f"未知 LLM provider: {settings.llm_provider}")
