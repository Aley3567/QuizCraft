"""系统级设置数据模型：KV 存储（LLM 配置等）。

切片 1.2：LLM 配置存为单行 JSON（value 文本列），敏感字段（api_key）落库前已加密。
provider/model/base_url 非敏感，明文存便于直接读取。
"""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from quizcraft.db import Base, TimestampMixin


class Setting(TimestampMixin, Base):
    """KV 配置存储：key 主键 + value（JSON 文本，敏感字段已加密）。"""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
