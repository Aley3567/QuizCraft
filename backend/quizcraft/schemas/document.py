"""文档相关 Pydantic 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from quizcraft.models.document import DocumentStatus


class SectionOut(BaseModel):
    """文档结构分块响应：携带 section_path / page_number，是错题引用原文的数据基础。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    section_path: str
    page_number: int
    token_count: int | None
    order_index: int
    content: str


class DocumentOut(BaseModel):
    """文档元信息响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    page_count: int | None
    status: DocumentStatus
    section_count: int = 0
    created_at: datetime | None = None


class DocumentDetail(DocumentOut):
    """文档详情：含解析出的结构分块列表。"""

    sections: list[SectionOut] = []
