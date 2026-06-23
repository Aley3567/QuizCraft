"""Mock LLM 客户端：测试用，按队列返回预设响应，不依赖真实 API。"""
from __future__ import annotations

from quizcraft.services.llm.base import LLMResponse, Message


class MockLLMClient:
    """注入预设响应队列；complete 依次弹出，耗尽后重复最后一条。

    记录所有调用到 self.calls，便于测试断言 LLM 收到的输入。
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])
        self._index = 0
        self.calls: list[list[Message]] = []

    async def complete(self, messages: list[Message], **kwargs) -> LLMResponse:
        self.calls.append(list(messages))
        if not self._responses:
            content = ""
        elif self._index < len(self._responses):
            content = self._responses[self._index]
            self._index += 1
        else:
            content = self._responses[-1]  # 队列耗尽后停在最后一条
        return LLMResponse(content=content)
