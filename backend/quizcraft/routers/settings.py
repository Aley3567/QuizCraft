"""settings 路由：LLM 配置的读取与保存 + 连通测试。

GET /api/settings/llm：返回脱敏配置视图（明文 api_key 永不离开后端），未配置 404。
POST /api/settings/llm：保存配置（api_key 加密落库）+ 立即连通测试，返回脱敏视图 + 连通结果。

连通失败不阻止保存——用户可据结果调整配置；但有 api_key 且未配置 secret 时拒绝保存，
避免明文落库敏感凭证。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.config import get_settings
from quizcraft.dependencies import get_session
from quizcraft.schemas.settings import (
    ConnectionResultOut,
    LLMConfigOut,
    LLMConfigRequest,
    LLMConfigSaveResponse,
    ReviewSettingsOut,
    ReviewSettingsRequest,
)
from quizcraft.services.settings import (
    LLMConfig,
    ReviewSettings,
    check_llm_connection,
    load_llm_config,
    load_llm_config_view,
    load_review_settings,
    save_llm_config,
    save_review_settings,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/llm", response_model=LLMConfigOut)
async def get_llm_settings(
    session: AsyncSession = Depends(get_session),
) -> LLMConfigOut:
    """返回脱敏 LLM 配置；未配置返回 404。"""
    view = await load_llm_config_view(session)
    if view is None:
        raise HTTPException(status_code=404, detail="尚未配置 LLM")
    return LLMConfigOut.model_validate(view)


@router.post("/llm", response_model=LLMConfigSaveResponse)
async def save_llm_settings(
    body: LLMConfigRequest,
    session: AsyncSession = Depends(get_session),
) -> LLMConfigSaveResponse:
    """保存 LLM 配置（api_key 加密落库）并测试连通，返回脱敏视图 + 连通结果。"""
    secret = get_settings().secret_key or ""
    api_key = body.api_key
    if "api_key" not in body.model_fields_set:
        try:
            existing = await load_llm_config(session, secret)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if existing is not None:
            api_key = existing.api_key

    config = LLMConfig(
        provider=body.provider,
        api_key=api_key,
        model=body.model,
        base_url=body.base_url,
    )

    # 先保存：有 api_key 但 secret 缺失 → 拒绝（不 fallback 明文落库）
    try:
        await save_llm_config(session, config, secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 再连通测试：用提交的明文配置探测（mock 无需外部连接；openai 真实调用，失败仅报告不阻断）
    connection = await check_llm_connection(
        provider=body.provider,
        api_key=api_key,
        model=body.model,
        base_url=body.base_url,
    )

    view = await load_llm_config_view(session)
    return LLMConfigSaveResponse(
        config=LLMConfigOut.model_validate(view),
        connection=ConnectionResultOut.model_validate(connection),
    )


@router.get("/review", response_model=ReviewSettingsOut)
async def get_review_settings(
    session: AsyncSession = Depends(get_session),
) -> ReviewSettingsOut:
    """Return flashcard review preferences, including defaults before first save."""
    return ReviewSettingsOut.model_validate(await load_review_settings(session))


@router.put("/review", response_model=ReviewSettingsOut)
async def update_review_settings(
    body: ReviewSettingsRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewSettingsOut:
    """Persist flashcard review preferences."""
    settings = ReviewSettings(
        desired_retention=body.desired_retention,
        daily_new_limit=body.daily_new_limit,
        daily_review_limit=body.daily_review_limit,
    )
    await save_review_settings(session, settings)
    return ReviewSettingsOut.model_validate(settings)


__all__ = ["router"]
