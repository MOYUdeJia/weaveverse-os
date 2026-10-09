"""Substring search across navigation, groups, books, and block content.

No full-text index. SQLite LIKE is enough while the library stays small.
"""

from __future__ import annotations

from sqlmodel import Session, col, select

from app.models import Block, Book, Group, NavItem


def _like(query: str) -> str:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _snippet(raw: str, query: str) -> str:
    folded = raw.casefold()
    at = folded.find(query.casefold())
    if at < 0:
        text = raw[:80]
    else:
        start = max(0, at - 28)
        end = min(len(raw), at + len(query) + 28)
        text = raw[start:end]
        if start:
            text = f"…{text}"
        if end < len(raw):
            text = f"{text}…"
    return " ".join(text.split())


def search_library(session: Session, query: str, limit: int = 12) -> dict:
    text = query.strip()
    empty = {"query": text, "nav": [], "groups": [], "books": [], "blocks": []}
    if not text:
        return empty

    pattern = _like(text)
    nav_rows = session.exec(
        select(NavItem)
        .where(col(NavItem.title).like(pattern, escape="\\") | col(NavItem.icon).like(pattern, escape="\\"))
        .limit(limit)
    ).all()
    group_rows = session.exec(
        select(Group).where(col(Group.name).like(pattern, escape="\\")).limit(limit)
    ).all()
    book_rows = session.exec(
        select(Book)
        .where(col(Book.title).like(pattern, escape="\\") | col(Book.author).like(pattern, escape="\\"))
        .limit(limit)
    ).all()
    shelf = session.exec(select(NavItem).where(NavItem.page_type == "bookshelf")).first()
    block_rows = session.exec(
        select(Block, NavItem)
        .join(NavItem, NavItem.id == Block.nav_item_id)
        .where(col(Block.content).like(pattern, escape="\\"))
        .limit(limit)
    ).all()

    return {
        "query": text,
        "nav": [
            {
                "id": item.id,
                "group_id": item.group_id,
                "title": item.title,
                "icon": item.icon,
                "page_type": item.page_type,
            }
            for item in nav_rows
        ],
        "groups": [
            {"id": group.id, "name": group.name, "icon": group.icon}
            for group in group_rows
        ],
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "nav_id": shelf.id if shelf is not None else None,
                "group_id": shelf.group_id if shelf is not None else None,
            }
            for book in book_rows
        ],
        "blocks": [
            {
                "block_id": block.id,
                "nav_id": item.id,
                "group_id": item.group_id,
                "title": item.title,
                "icon": item.icon,
                "block_type": block.block_type,
                "snippet": _snippet(block.content, text),
            }
            for block, item in block_rows
        ],
    }
