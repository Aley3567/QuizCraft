"""测试公共夹具：内存 SQLite 引擎 + 会话 + HTTP 客户端。"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from quizcraft.config import Settings
from quizcraft.db import Base

import quizcraft.models  # noqa: F401  注册 ORM 模型到 Base.metadata，供 create_all 建表


@pytest_asyncio.fixture
async def engine():
    """每个测试用独立的内存 SQLite，并建好全部表。"""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """直接操作 ORM 的 async session（用于模型层测试）。"""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine):
    """覆盖 DB 依赖的 HTTP 客户端（用于路由层测试）。"""
    from httpx import ASGITransport, AsyncClient

    from quizcraft.dependencies import get_session
    from quizcraft.main import app

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def settings():
    """默认 mock provider 的配置，测试不依赖真实 key。"""
    return Settings(llm_provider="mock")
