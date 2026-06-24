"""LLM 配置的加密存储与读取。

切片 1.2：LLM 配置（provider/api_key/model/base_url）以 JSON 存入 settings 表的
单行 KV（key="llm_config"）。provider/model/base_url 非敏感明文存；api_key 落库前
Fernet 加密、读取时解密，secret 从 QUIZCRAFT_SECRET_KEY 派生。

无 api_key 的配置（mock provider）不需 secret 也能存（无敏感数据无需加密）；
有 api_key 但 secret 缺失时拒绝保存，避免明文落库敏感凭证。
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.models.setting import Setting
from quizcraft.services.settings.crypto import decrypt_or_none, encrypt_or_none

LLM_CONFIG_KEY = "llm_config"
REVIEW_SETTINGS_KEY = "review_settings"


@dataclass
class LLMConfig:
    """LLM 配置（内存表示）：api_key 为明文，仅用于连通测试与运行时构建 client。

    落库前由 save_llm_config 加密；读取后由 load_llm_config 解密回明文。
    """

    provider: str
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None


@dataclass
class LLMConfigView:
    """LLM 配置脱敏视图（供前端展示）：不含明文 api_key，仅 has_api_key 标识。

    GET /api/settings/llm 返回此视图——明文 key 永不离开后端，避免序列化泄露。
    """

    provider: str
    has_api_key: bool
    model: str | None
    base_url: str | None


@dataclass
class ReviewSettings:
    """Flashcard review preferences stored as plain JSON."""

    desired_retention: float = 0.9
    daily_new_limit: int = 20
    daily_review_limit: int = 200


async def save_llm_config(session: AsyncSession, config: LLMConfig, secret: str) -> None:
    """加密 api_key 并 upsert 到 settings 表（同 key 覆盖）。

    api_key 非空但 secret 为空时 encrypt_or_none 抛 ValueError——调用方需提示配置 secret。
    """
    encrypted_key = encrypt_or_none(config.api_key, secret)  # None 透传，非空要求 secret
    payload = json.dumps(
        {
            "provider": config.provider,
            "api_key_encrypted": encrypted_key,
            "model": config.model,
            "base_url": config.base_url,
        },
        ensure_ascii=False,
    )

    existing = await session.get(Setting, LLM_CONFIG_KEY)
    if existing is None:
        session.add(Setting(key=LLM_CONFIG_KEY, value=payload))
    else:
        existing.value = payload
    await session.commit()


async def load_llm_config(session: AsyncSession, secret: str) -> LLMConfig | None:
    """读取并解密 LLM 配置；未配置返回 None。

    api_key_encrypted 为空（mock provider 等无 key 配置）时返回 api_key=None，不需解密。
    """
    row = (
        await session.execute(select(Setting).where(Setting.key == LLM_CONFIG_KEY))
    ).scalar_one_or_none()
    if row is None or row.value is None:
        return None

    data = json.loads(row.value)
    return LLMConfig(
        provider=data["provider"],
        api_key=decrypt_or_none(data.get("api_key_encrypted"), secret),
        model=data.get("model"),
        base_url=data.get("base_url"),
    )


async def load_llm_config_view(session: AsyncSession) -> LLMConfigView | None:
    """读取 LLM 配置的脱敏视图（不解密 api_key）。

    供 GET /api/settings/llm：不需 secret，不暴露明文 key，仅以 has_api_key 标识是否已配置。
    """
    row = (
        await session.execute(select(Setting).where(Setting.key == LLM_CONFIG_KEY))
    ).scalar_one_or_none()
    if row is None or row.value is None:
        return None

    data = json.loads(row.value)
    return LLMConfigView(
        provider=data["provider"],
        has_api_key=bool(data.get("api_key_encrypted")),
        model=data.get("model"),
        base_url=data.get("base_url"),
    )


async def save_review_settings(session: AsyncSession, settings: ReviewSettings) -> None:
    """Persist flashcard review preferences in the settings KV table."""
    payload = json.dumps(
        {
            "desired_retention": settings.desired_retention,
            "daily_new_limit": settings.daily_new_limit,
            "daily_review_limit": settings.daily_review_limit,
        },
        ensure_ascii=False,
    )
    existing = await session.get(Setting, REVIEW_SETTINGS_KEY)
    if existing is None:
        session.add(Setting(key=REVIEW_SETTINGS_KEY, value=payload))
    else:
        existing.value = payload
    await session.commit()


async def load_review_settings(session: AsyncSession) -> ReviewSettings:
    """Load flashcard review preferences, returning defaults before first save."""
    row = (
        await session.execute(select(Setting).where(Setting.key == REVIEW_SETTINGS_KEY))
    ).scalar_one_or_none()
    if row is None or row.value is None:
        return ReviewSettings()

    data = json.loads(row.value)
    defaults = ReviewSettings()
    return ReviewSettings(
        desired_retention=data.get("desired_retention", defaults.desired_retention),
        daily_new_limit=data.get("daily_new_limit", defaults.daily_new_limit),
        daily_review_limit=data.get("daily_review_limit", defaults.daily_review_limit),
    )
