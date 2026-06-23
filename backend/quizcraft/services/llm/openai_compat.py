"""OpenAI 兼容 LLM 客户端。

通过 openai SDK 的 AsyncOpenAI 调用任意 OpenAI 兼容端点
（OpenAI 官方、Claude 的 OpenAI 兼容端点、Ollama 等），base_url 可配。
真实调用需要 yufeng 配置 API key，测试不覆盖真实调用（记 blocker 跳过）。
"""
from __future__ import annotations

from openai import AsyncOpenAI

from quizcraft.services.llm.base import LLMResponse, Message


class OpenAICompatibleClient:
    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        if not api_key:
            raise ValueError("OpenAI-compatible LLM 需要 api_key")
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def complete(self, messages: list[Message], **kwargs) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs,
        )
        choice = resp.choices[0]
        usage = {}
        if resp.usage is not None:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
            }
        return LLMResponse(content=choice.message.content or "", usage=usage)
