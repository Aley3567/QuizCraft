"""FastAPI 依赖：DB session 与 LLM client。"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from quizcraft.config import get_settings
from quizcraft.db import make_engine, make_session_factory
from quizcraft.services.llm import LLMClient, make_llm_client

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


def get_llm_client() -> LLMClient:
    """返回按配置构建的 LLM client（默认 mock，测试不依赖真实 key）。"""
    return make_llm_client(get_settings())
