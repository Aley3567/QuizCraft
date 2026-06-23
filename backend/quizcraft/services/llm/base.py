"""LLM 抽象层接口。

QuizCraft 的 LLM 可插拔：测试用 MockLLMClient，真实环境用 OpenAICompatibleClient
（覆盖 Claude/GPT via OpenAI 兼容端点，Ollama 延后）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    usage: dict = field(default_factory=dict)  # {prompt_tokens, completion_tokens, ...}


class LLMClient(Protocol):
    """LLM 客户端契约：给定消息列表返回补全响应。"""

    async def complete(self, messages: list[Message], **kwargs) -> LLMResponse:
        ...
