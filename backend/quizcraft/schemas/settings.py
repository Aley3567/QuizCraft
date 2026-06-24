"""settings 相关 Pydantic 请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LLMConfigRequest(BaseModel):
    """POST /api/settings/llm 请求：LLM 配置（api_key 为明文，落库前加密）。"""

    provider: str
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None


class LLMConfigOut(BaseModel):
    """GET 响应：脱敏配置视图，明文 api_key 永不离开后端。"""

    model_config = ConfigDict(from_attributes=True)

    provider: str
    has_api_key: bool
    model: str | None
    base_url: str | None


class ConnectionResultOut(BaseModel):
    """连通测试结果（从 ConnectionResult dataclass 转换）。"""

    model_config = ConfigDict(from_attributes=True)

    ok: bool
    provider: str
    model: str | None
    message: str


class LLMConfigSaveResponse(BaseModel):
    """POST 响应：保存后的脱敏配置 + 连通测试结果。"""

    config: LLMConfigOut
    connection: ConnectionResultOut


class ReviewSettingsRequest(BaseModel):
    """PUT /api/settings/review 请求：闪卡复习偏好。"""

    desired_retention: float = Field(ge=0.5, le=0.99)
    daily_new_limit: int = Field(ge=0)
    daily_review_limit: int = Field(ge=0)


class ReviewSettingsOut(BaseModel):
    """Flashcard review settings response."""

    model_config = ConfigDict(from_attributes=True)

    desired_retention: float
    daily_new_limit: int
    daily_review_limit: int
