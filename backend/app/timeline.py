"""Aggregate quick notes, reader notes, new pages, and finished focus intervals.

Relational rows come from one UNION. Inbox lines stay inside a block's JSON,
so they are parsed and merged afterwards. They are not a table of their own.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import text
from sqlmodel import Session, select

from app import crud
from app.crud import TitleConflict
from app.errors import raise_api_error
from app.group_crud import get_system_group
from app.models import Block, FocusSession, NavItem, utc_now
from app.schemas import NavItemCreate


UNION_SQL = """
SELECT kind, source_id, at, title, body, extra, book_id, position, nav_id, group_id, icon
FROM (
    SELECT
        'read' AS kind,
        book_notes.id AS source_id,
        book_notes.created_at AS at,
        books.title AS title,
        book_notes.note_content AS body,
        book_notes.text AS extra,
        book_notes.book_id AS book_id,
        book_notes.position AS position,
        NULL AS nav_id,
        NULL AS group_id,
        '📖' AS icon
    FROM book_notes
    JOIN books ON books.id = book_notes.book_id
    WHERE book_notes.type = 'note'
    UNION ALL
    SELECT
        'page' AS kind,
        nav_items.id AS source_id,
        nav_items.created_at AS at,
        nav_items.title AS title,
        nav_items.page_type AS body,
        '' AS extra,
        NULL AS book_id,
        '' AS position,
        nav_items.id AS nav_id,
        nav_items.group_id AS group_id,
        nav_items.icon AS icon
    FROM nav_items
    WHERE nav_items.page_type NOT IN ('timeline', 'group_overview')
    UNION ALL
    SELECT
        'focus' AS kind,
        focus_sessions.id AS source_id,
        focus_sessions.completed_at AS at,
        focus_sessions.label AS title,
        '' AS body,
        CAST(focus_sessions.minutes AS TEXT) AS extra,
        NULL AS book_id,
        '' AS position,
        NULL AS nav_id,
        NULL AS group_id,
        '🍅' AS icon
    FROM focus_sessions
) AS events
ORDER BY at DESC
LIMIT 400
"""


def ensure_timeline_page(session: Session) -> NavItem:
    existing = session.exec(select(NavItem).where(NavItem.page_type == "timeline")).first()
    if existing is not None:
        return existing
    system = get_system_group(session)
    if system is None or system.id is None:
        raise_api_error(500, "group_id", "缺少系统分组")
    title = "时间线"
    taken = session.exec(
        select(NavItem.id).where(NavItem.group_id == system.id, NavItem.title == title)
    ).first()
    if taken is not None:
        title = "时间线记录"
    try:
        return crud.create_nav_item(
            session,
            NavItemCreate(title=title, icon="⏳", page_type="timeline"),
            page_type="timeline",
            group_id=system.id,
        )
    except TitleConflict:
        raise_api_error(409, "title", "系统分组里已有同名页面，时间线建不出来")


def record_focus(session: Session, minutes: int) -> FocusSession:
    minutes = 25 if minutes != 25 else minutes
    row = FocusSession(
        minutes=minutes,
        label=f"完成了一次 {minutes} 分钟专注",
        completed_at=utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _iso(value) -> str:
    if isinstance(value, datetime):
        moment = value
    else:
        raw = str(value or "").strip().replace("Z", "+00:00")
        if not raw:
            return ""
        raw = raw.replace(" ", "T", 1) if "T" not in raw and " " in raw else raw
        moment = datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.isoformat()


def _local_stamp(stamp: str) -> str:
    text_value = str(stamp or "").strip()
    if not text_value:
        return ""
    try:
        moment = datetime.strptime(text_value, "%Y-%m-%d %H:%M")
    except ValueError:
        return ""
    return moment.astimezone().isoformat()


def _inbox_events(session: Session) -> list[dict]:
    item = session.exec(select(NavItem).where(NavItem.page_type == "inbox")).first()
    if item is None or item.id is None:
        return []
    block = session.exec(
        select(Block).where(Block.nav_item_id == item.id).order_by(Block.sort_order)
    ).first()
    if block is None:
        return []
    try:
        content = json.loads(block.content or "{}")
    except json.JSONDecodeError:
        return []
    lines = content.get("lines") if isinstance(content, dict) else None
    if not isinstance(lines, list):
        return []
    events = []
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            continue
        text_value = str(line.get("text") or "").strip()
        if not text_value:
            continue
        events.append(
            {
                "id": f"inbox-{index}-{line.get('at') or index}",
                "kind": "note",
                "at": _local_stamp(str(line.get("at") or "")),
                "title": text_value.replace("\n", " ")[:80],
                "summary": text_value[:180],
                "icon": "📝",
                "nav_id": item.id,
                "group_id": item.group_id,
                "book_id": None,
                "position": "",
            }
        )
    return events


def _shelf(session: Session) -> NavItem | None:
    return session.exec(select(NavItem).where(NavItem.page_type == "bookshelf")).first()


def list_events(session: Session) -> list[dict]:
    shelf = _shelf(session)
    rows = session.connection().execute(text(UNION_SQL)).mappings().all()
    events: list[dict] = []
    for row in rows:
        kind = row["kind"]
        nav_id = row["nav_id"]
        group_id = row["group_id"]
        if kind == "read" and shelf is not None:
            nav_id = shelf.id
            group_id = shelf.group_id
        title = str(row["title"] or "").strip()
        body = str(row["body"] or "").strip()
        extra = str(row["extra"] or "").strip()
        icon = str(row["icon"] or "📄")
        if icon.startswith("@file:"):
            icon = "📄"
        if kind == "read":
            summary = body or extra
            title = title or "阅读笔记"
        elif kind == "focus":
            summary = title or "完成了一次专注"
            title = summary
        else:
            summary = title
        events.append(
            {
                "id": f"{kind}-{row['source_id']}",
                "kind": kind,
                "at": _iso(row["at"]),
                "title": title[:80],
                "summary": summary[:180],
                "icon": icon,
                "nav_id": nav_id,
                "group_id": group_id,
                "book_id": row["book_id"],
                "position": row["position"] or "",
            }
        )
    events.extend(_inbox_events(session))
    events.sort(key=lambda item: item["at"] or "", reverse=True)
    return events[:400]
