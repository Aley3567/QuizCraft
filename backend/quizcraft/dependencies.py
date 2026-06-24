"""FastAPI 依赖：DB session 与 LLM client。"""
from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.config import Settings, get_settings
from quizcraft.db import make_engine, make_session_factory
from quizcraft.services.llm import LLMClient, make_llm_client
from quizcraft.services.settings import load_llm_config

# 模块级单例引擎与会话工厂（按默认配置懒创建；测试用 dependency_overrides 替换 get_session）
_engine = None
_session_factory = None


def _get_factory():
    global _engine, _session_factory
    if _session_factory is None:
        settings = get_settings()
        _engine = make_engine(settings.db_url)
        _session_factory = make_session_factory(_engine)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """提供请求级 DB session，结束自动关闭。"""
    factory = _get_factory()
    async with factory() as session:
        yield session


async def resolve_llm_settings(session: AsyncSession, settings: Settings) -> Settings:
    """返回运行时应使用的 LLM Settings：优先 DB 配置，回退 env 配置。

    子系统1 运行时增量：用户在 Settings 页保存配置后，出题/答题无需重启即读 DB 生效。
    DB 无配置 / 读取异常（secret 缺失或解密失败）→ 回退 env，不阻断出题（保守降级）。

    DB 配置已成功解密但 make_llm_client 构造失败（如 openai 在缺 socksio 的代理环境）
    不在此兜底——让错误上浮（路由 500），避免静默降级到 mock 让用户用错配置出题。
    """
    secret = settings.secret_key or ""
    try:
        db_config = await load_llm_config(session, secret)
    except Exception:  # noqa: BLE001 secret 缺失/解密失败等回退 env，不阻断出题
        return settings
    if db_config is None:
        return settings
    return settings.model_copy(
        update={
            "llm_provider": db_config.provider,
            "llm_api_key": db_config.api_key,
            "llm_model": db_config.model or settings.llm_model,
            "llm_base_url": db_config.base_url,
        }
    )


async def get_llm_client(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[LLMClient]:
    """返回运行时 LLM client：优先按 DB 配置构建，未配置回退 env。

    Depends(get_session) 复用请求级 session（FastAPI sub-dependency 去重，同请求共享）。
    """
    settings = get_settings()
    resolved = await resolve_llm_settings(session, settings)
    yield make_llm_client(resolved)
