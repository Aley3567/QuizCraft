"""FastAPI 应用入口。"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine

from quizcraft import __version__
from quizcraft.config import get_settings
from quizcraft.db import Base
from quizcraft.routers import (
    documents_router,
    quiz_router,
    quiz_sessions_router,
    settings_router,
)

import quizcraft.models  # noqa: F401  注册 ORM 模型到 Base.metadata，供 create_all 建表


def _ensure_data_dir(db_url: str) -> None:
    """SQLite 文件 DB 需数据目录存在（内存 DB 跳过）。"""
    if ":memory:" in db_url:
        return
    path = db_url.split(":///", 1)[-1]  # 取 /// 之后的文件路径部分
    parent = Path(path).parent
    if str(parent) and str(parent) != ".":
        os.makedirs(parent, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动建表：切片 1.1 单机原型用 create_all 自动建表（生产可换 Alembic 迁移）。

    真机 dev/部署首启需建表，否则 INSERT 报无表 500。
    测试用内存 SQLite + conftest 的 create_all，不走本 lifespan（ASGITransport 不触发 startup）。
    """
    settings = get_settings()
    _ensure_data_dir(settings.db_url)
    engine = create_async_engine(settings.db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    yield


app = FastAPI(title="QuizCraft API", version=__version__, lifespan=lifespan)

# CORS：放行前端源（默认 Next.js dev server :3000），自部署按 env 覆盖。
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(quiz_router)
app.include_router(quiz_sessions_router)
app.include_router(settings_router)


@app.get("/health")
async def health() -> dict:
    """健康检查。"""
    return {"status": "ok"}
