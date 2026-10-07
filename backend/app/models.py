"""Database models for Weaveverse OS.

Defines SQLModel tables only. No HTTP or business logic lives here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


# 返回带时区的 UTC 当前时间。
# Return the current timezone-aware UTC datetime.
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NavItem(SQLModel, table=True):
    """A top-level workspace entry shown in the sidebar."""

    __tablename__ = "nav_items"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(min_length=1, max_length=50, nullable=False)
    icon: str = Field(min_length=1, max_length=20, nullable=False)
    sort_order: int = Field(default=0, nullable=False, index=True)
    page_type: str = Field(default="markdown", max_length=50, nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class Block(SQLModel, table=True):
    """A content unit that belongs to one navigation page."""

    __tablename__ = "blocks"

    id: int | None = Field(default=None, primary_key=True)
    nav_item_id: int = Field(
        foreign_key="nav_items.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    block_type: str = Field(max_length=32, nullable=False)
    content: str = Field(
        default="{}",
        sa_column=Column(Text, nullable=False, server_default="{}"),
    )
    sort_order: int = Field(default=0, nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
