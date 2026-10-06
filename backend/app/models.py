"""Database models for Weaveverse OS."""
#只定义数据结构
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.utcnow()


class NavItem(SQLModel, table=True):
    """A top-level workspace entry shown in the sidebar."""

    __tablename__ = "nav_items"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(min_length=1, max_length=50, nullable=False)
    icon: str = Field(min_length=1, max_length=8, nullable=False)
    sort_order: int = Field(default=0, nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
