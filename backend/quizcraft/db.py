"""SQLAlchemy async 引擎、会话工厂与声明基类。"""
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """所有 ORM 模型的声明基类（async 属性懒加载）。"""


class TimestampMixin:
    """created_at / updated_at 自动维护。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


def make_engine(db_url: str):
    """按 db_url 创建 async 引擎；SQLite 关闭同线程校验以兼容 FastAPI 线程模型。"""
    connect_args: dict = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(db_url, connect_args=connect_args)


def make_session_factory(engine):
    """创建 async session 工厂（expire_on_commit=False，commit 后对象仍可用）。"""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
