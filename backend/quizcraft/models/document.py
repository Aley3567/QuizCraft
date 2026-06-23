"""文档相关数据模型：Document、Section、Concept。

    Document -> Section（结构分块）-> Concept（概念）

source_span（文档原文位置：page/section_path/text）是 QuizCraft「用用户文档解释错题」
的数据基础，Concept 与 Question 都必须携带。
"""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from quizcraft.db import Base, TimestampMixin


class DocumentStatus(str, Enum):
    """文档解析状态：切片 1.1 只用 pending/complete，processing/failed 留给切片 1.4。"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False
    )

    sections: Mapped[list[Section]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Section(TimestampMixin, Base):
    """文档结构分块（512-1024 token），保留章节路径与页码元数据。"""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    section_path: Mapped[str] = mapped_column(String(512))  # 如 "第2章 > 2.1 节"
    page_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped[Document] = relationship(back_populates="sections")
    concepts: Mapped[list[Concept]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


class Concept(TimestampMixin, Base):
    """从文档分块提取的学习概念（两步生成法 Step 1 产物）。"""

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_span: Mapped[dict] = mapped_column(JSON)  # {page, section_path, text}
    bloom_level: Mapped[str | None] = mapped_column(String(64), nullable=True)

    section: Mapped[Section | None] = relationship(back_populates="concepts")
