"""Tools the chat model may call. Writes go through existing crud functions.

This module does not read or log API keys.
"""

from __future__ import annotations

import json

from sqlmodel import Session, col, select

from app import crud, group_crud
from app.crud import TitleConflict
from app.group_crud import get_system_group
from app.models import Book, Group
from app.page_types import PAGE_TYPES, default_icon_for
from app.routes.inbox import add_note
from app.schemas import NavItemCreate, QuickNoteCreate
from app.search import search_library

CREATABLE = {"doc", "plain", "bookmarks", "canvas", "markdown", "todo", "gallery", "collection"}

TOOLS = [
    {
        "name": "list_groups",
        "description": "列出全部分组的名字。",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_items",
        "description": "按关键词搜索页面、分组和书籍。",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_page_content",
        "description": "读取一个页面的标题和正文摘要。",
        "parameters": {
            "type": "object",
            "properties": {"nav_id": {"type": "integer"}},
            "required": ["nav_id"],
        },
    },
    {
        "name": "create_page",
        "description": "新建一个页面。不能修改已有页面。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "page_type": {"type": "string", "enum": sorted(CREATABLE)},
                "group_name": {"type": "string"},
            },
            "required": ["title", "page_type"],
        },
    },
    {
        "name": "create_group",
        "description": "新建一个分组。",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "create_quick_note",
        "description": "在收件箱记一条速记。",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}},
            "required": ["text"],
        },
    },
]

WRITE_TOOLS = {"create_page", "create_group", "create_quick_note"}


def is_write(name: str) -> bool:
    return name in WRITE_TOOLS


def summarize_call(name: str, arguments: dict) -> str:
    if name == "create_page":
        return f"创建页面「{arguments.get('title') or '未命名'}」"
    if name == "create_group":
        return f"创建分组「{arguments.get('name') or '未命名'}」"
    if name == "create_quick_note":
        return "记一条速记"
    if name == "search_items":
        return f"搜索「{arguments.get('query') or ''}」"
    if name == "get_page_content":
        return "读取页面"
    if name == "list_groups":
        return "查看分组"
    return name


def run_tool(session: Session, name: str, arguments: dict) -> dict:
    if name == "list_groups":
        return _list_groups(session)
    if name == "search_items":
        return _search(session, str(arguments.get("query") or ""))
    if name == "get_page_content":
        return _page(session, arguments.get("nav_id"))
    if name == "create_page":
        return _create_page(session, arguments)
    if name == "create_group":
        return _create_group(session, str(arguments.get("name") or ""))
    if name == "create_quick_note":
        return _note(session, arguments)
    return {"ok": False, "error": "未知工具"}


def _list_groups(session: Session) -> dict:
    rows = [
        {"id": group.id, "name": group.name, "icon": group.icon}
        for group in group_crud.list_groups(session)
        if group.id is not None
    ]
    return {"ok": True, "groups": rows}


def _search(session: Session, query: str) -> dict:
    found = search_library(session, query, limit=12)
    pattern = f"%{query.strip()}%"
    groups = session.exec(select(Group).where(col(Group.name).like(pattern))).all()
    books = session.exec(select(Book).where(col(Book.title).like(pattern)).limit(8)).all()
    return {
        "ok": True,
        "pages": [
            {"id": hit["id"], "group_id": hit["group_id"], "title": hit["title"], "path": hit["path"]}
            for hit in found.get("nav") or []
        ],
        "groups": [{"id": group.id, "name": group.name} for group in groups],
        "books": [{"id": book.id, "title": book.title} for book in books],
    }


def _page(session: Session, nav_id: object) -> dict:
    try:
        item_id = int(nav_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "页面不存在"}
    item = crud.get_nav_item(session, item_id)
    if item is None:
        return {"ok": False, "error": "页面不存在"}
    detail = crud.nav_item_to_detail(session, item)
    raw = json.dumps(detail.get("blocks") or [], ensure_ascii=False)
    return {
        "ok": True,
        "id": detail["id"],
        "group_id": detail["group_id"],
        "title": detail["title"],
        "page_type": detail["page_type"],
        "excerpt": raw[:2500],
    }


def _group_id(session: Session, name: str) -> int:
    wanted = name.strip()
    if wanted:
        for group in group_crud.list_groups(session):
            if group.name == wanted and group.id is not None:
                return group.id
    system = get_system_group(session)
    if system is None or system.id is None:
        raise ValueError("没有可用的分组")
    return system.id


def _create_page(session: Session, arguments: dict) -> dict:
    title = str(arguments.get("title") or "").strip()[:50]
    page_type = str(arguments.get("page_type") or "")
    if page_type not in CREATABLE:
        return {"ok": False, "error": "这个页面类型不能由助手创建"}
    if not title:
        return {"ok": False, "error": "需要页面标题"}
    icon = default_icon_for(page_type) or "📄"
    try:
        item = crud.create_nav_item(
            session,
            NavItemCreate(title=title, icon=icon, page_type=page_type),
            page_type=page_type,
            group_id=_group_id(session, str(arguments.get("group_name") or "")),
        )
    except TitleConflict:
        return {"ok": False, "error": "这个分组里已经有同名页面"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "id": item.id,
        "group_id": item.group_id,
        "title": item.title,
        "summary": f"已创建「{item.title}」页",
    }


def _create_group(session: Session, name: str) -> dict:
    cleaned = name.strip()[:50]
    if not cleaned:
        return {"ok": False, "error": "需要分组名"}
    try:
        group = group_crud.create_group(session, cleaned, "📁")
    except Exception as exc:
        return {"ok": False, "error": str(exc) or "分组没建成"}
    return {"ok": True, "id": group.id, "name": group.name, "summary": f"已创建分组「{group.name}」"}


def _note(session: Session, arguments: dict) -> dict:
    text = str(arguments.get("text") or "").strip()
    tags = arguments.get("tags") if isinstance(arguments.get("tags"), list) else []
    if not text:
        return {"ok": False, "error": "速记是空的"}
    saved = add_note(QuickNoteCreate(text=text, tags=[str(tag) for tag in tags]), session)
    return {"ok": True, "summary": "已记到收件箱", "id": saved.get("id"), "group_id": saved.get("group_id")}
