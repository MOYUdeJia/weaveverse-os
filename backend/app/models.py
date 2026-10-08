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


class Group(SQLModel, table=True):
    """A sidebar folder that owns navigation items and one overview page."""

    __tablename__ = "groups"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=50, nullable=False)
    icon: str = Field(min_length=1, max_length=20, nullable=False)
    description: str = Field(
        default="",
        sa_column=Column(Text, nullable=False, server_default=""),
    )
    is_system: bool = Field(default=False, nullable=False, index=True)
    sort_order: int = Field(default=0, nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class NavItem(SQLModel, table=True):
    """A top-level workspace entry shown in the sidebar."""

    __tablename__ = "nav_items"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(min_length=1, max_length=50, nullable=False)
    icon: str = Field(min_length=1, max_length=20, nullable=False)
    sort_order: int = Field(default=0, nullable=False, index=True)
    page_type: str = Field(default="markdown", max_length=50, nullable=False, index=True)
    group_id: int = Field(
        foreign_key="groups.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    pinned: bool = Field(default=False, nullable=False)
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


class Book(SQLModel, table=True):
    """One imported EPUB, TXT, or PDF plus its reading progress.

    Books belong to the single bookshelf, not to a nav item.
    Chapter HTML stays in the original file; toc stores titles and internal hrefs.
    """

    __tablename__ = "books"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=500, nullable=False)
    author: str = Field(default="", max_length=500, nullable=False)
    format: str = Field(max_length=8, nullable=False, index=True)
    original_filename: str = Field(max_length=255, nullable=False)
    file_size: int = Field(nullable=False)
    cover_ext: str | None = Field(default=None, max_length=8)
    language: str = Field(default="", max_length=32, nullable=False)
    description: str = Field(
        default="",
        sa_column=Column(Text, nullable=False, server_default=""),
    )
    text_encoding: str = Field(default="", max_length=32, nullable=False)
    chapter_count: int = Field(default=0, nullable=False)
    page_count: int = Field(default=0, nullable=False)
    toc: str = Field(
        default="[]",
        sa_column=Column(Text, nullable=False, server_default="[]"),
    )
    progress_chapter: int = Field(default=0, nullable=False)
    progress_offset: float = Field(default=0.0, nullable=False)
    progress_ratio: float = Field(default=0.0, nullable=False)
    last_read_at: datetime | None = Field(default=None, nullable=True, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
