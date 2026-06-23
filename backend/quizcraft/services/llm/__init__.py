"""LLM 抽象层：可插拔的 LLM 客户端。"""
from quizcraft.services.llm.base import LLMClient, LLMResponse, Message
from quizcraft.services.llm.factory import make_llm_client
from quizcraft.services.llm.mock import MockLLMClient
from quizcraft.services.llm.openai_compat import OpenAICompatibleClient

__all__ = [
    "LLMClient",
    "LLMResponse",
    "Message",
    "MockLLMClient",
    "OpenAICompatibleClient",
    "make_llm_client",
]
