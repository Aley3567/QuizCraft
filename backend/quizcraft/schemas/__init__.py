"""Pydantic 请求/响应模型。"""
from quizcraft.schemas.document import DocumentDetail, DocumentOut, SectionOut
from quizcraft.schemas.settings import (
    ConnectionResultOut,
    LLMConfigOut,
    LLMConfigRequest,
    LLMConfigSaveResponse,
)

__all__ = [
    "ConnectionResultOut",
    "DocumentDetail",
    "DocumentOut",
    "LLMConfigOut",
    "LLMConfigRequest",
    "LLMConfigSaveResponse",
    "SectionOut",
]
