"""Search navigation titles. Focus pages also match their page tags.

Groups, books, and block text are not included.
"""

from __future__ import annotations

import json

from sqlmodel import Session, col, select

from app.models import Group, NavItem
from app.page_types import page_layer


def _like(query: str) -> str:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _tags(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item).strip().lstrip("#") for item in data if str(item).strip()]


def search_library(session: Session, query: str, limit: int = 30) -> dict:
    text = query.strip().lstrip("#").strip()
    if not text:
        return {"query": query.strip(), "nav": []}

    pattern = _like(text)
    rows = session.exec(
        select(NavItem, Group)
        .join(Group, Group.id == NavItem.group_id)
        .where(col(NavItem.title).like(pattern, escape="\\"))
        .limit(limit)
    ).all()
    seen = {item.id for item, _group in rows}
    focus_rows = session.exec(
        select(NavItem, Group)
        .join(Group, Group.id == NavItem.group_id)
        .where(NavItem.page_type.in_(["doc", "plain", "bookmarks", "canvas", "inbox"]))
    ).all()

    hits = []
    for item, group in rows:
        hits.append(_hit(item, group, "title"))
    for item, group in focus_rows:
        if item.id in seen:
            continue
        tags = _tags(item.tags)
        if any(text.casefold() in tag.casefold() for tag in tags):
            hits.append(_hit(item, group, "tag"))
            if len(hits) >= limit:
                break
    return {"query": query.strip(), "nav": hits[:limit]}


def _hit(item: NavItem, group: Group, matched: str) -> dict:
    return {
        "id": item.id,
        "group_id": item.group_id,
        "title": item.title,
        "icon": item.icon,
        "page_type": item.page_type,
        "layer": page_layer(item.page_type),
        "tags": _tags(item.tags),
        "matched": matched,
        "path": f"{group.name} > {item.title}",
    }
