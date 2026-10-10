"""Quick-capture notes land on the single inbox page."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app import crud
from app.crud import TitleConflict
from app.config import DATA_DIR
from app.db import get_session
from app.errors import raise_api_error
from app.group_crud import get_system_group
from app.models import Block, NavItem
from app.schemas import BlockUpdate, NavItemCreate, QuickNoteCreate


router = APIRouter(prefix="/inbox", tags=["inbox"])

QUICK_TAGS_PATH = DATA_DIR / "quick_tags.json"
DEFAULT_QUICK_TAGS = ["工作", "生活", "灵感", "待办"]


def _clean_tags(items: list, limit: int) -> list[str]:
    cleaned: list[str] = []
    for raw in items:
        text = str(raw).strip().lstrip("#").strip()
        if text and text not in cleaned:
            cleaned.append(text[:24])
        if len(cleaned) >= limit:
            break
    return cleaned


def _write_store(store: dict) -> None:
    QUICK_TAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"common": store["common"], "history": store["history"]}
    QUICK_TAGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _tag_store() -> dict:
    try:
        data = json.loads(QUICK_TAGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {"common": list(DEFAULT_QUICK_TAGS), "history": []}
    migrated = False
    if isinstance(data, list):
        store = {"common": _clean_tags(data, 6) or list(DEFAULT_QUICK_TAGS), "history": []}
        migrated = True
    elif isinstance(data, dict):
        common_source = data.get("common")
        if not isinstance(common_source, list):
            common_source = data.get("tags") if isinstance(data.get("tags"), list) else list(DEFAULT_QUICK_TAGS)
        history_source = data.get("history") if isinstance(data.get("history"), list) else []
        store = {
            "common": _clean_tags(common_source, 6) or list(DEFAULT_QUICK_TAGS),
            "history": _clean_tags(history_source, 100),
        }
    else:
        store = {"common": list(DEFAULT_QUICK_TAGS), "history": []}
        migrated = True
    if migrated:
        _write_store(store)
    return store


def _quick_tags() -> list[str]:
    return _tag_store()["common"]


def _write_quick_tags(tags: list[str]) -> list[str]:
    store = _tag_store()
    store["common"] = _clean_tags(tags, 6) or list(DEFAULT_QUICK_TAGS)
    _write_store(store)
    return store["common"]


def _remember_history(tags: list[str]) -> None:
    store = _tag_store()
    ordered: list[str] = []
    for raw in list(tags)[::-1] + store["history"]:
        text = str(raw).strip().lstrip("#").strip()[:24]
        if text and text not in ordered:
            ordered.append(text)
        if len(ordered) >= 100:
            break
    store["history"] = ordered
    _write_store(store)


@router.get("/tags")
def get_quick_tags() -> dict:
    store = _tag_store()
    return {"tags": store["common"], "common": store["common"], "history": store["history"]}


@router.put("/tags")
def put_quick_tags(data: dict) -> dict:
    tags = data.get("tags") if isinstance(data, dict) else None
    if tags is None and isinstance(data, dict):
        tags = data.get("common")
    if not isinstance(tags, list):
        raise_api_error(400, "tags", "需要标签数组")
    common = _write_quick_tags(tags)
    history = _tag_store()["history"]
    return {"tags": common, "common": common, "history": history}


def _inbox_item(session: Session) -> NavItem:
    existing = session.exec(select(NavItem).where(NavItem.page_type == "inbox")).first()
    if existing is not None:
        return existing

    system = get_system_group(session)
    if system is None or system.id is None:
        raise_api_error(500, "group_id", "缺少系统分组")
    try:
        return crud.create_nav_item(
            session,
            NavItemCreate(title="收件箱", icon="📥", page_type="inbox"),
            page_type="inbox",
            group_id=system.id,
        )
    except TitleConflict:
        raise_api_error(409, "title", "系统分组里已有同名页面，收件箱建不出来")


@router.post("/notes")
# 把一条速记追加到收件箱。没有收件箱就先建在系统分组。
# Append one quick note. Create the inbox in the system group when it is missing.
def add_note(data: QuickNoteCreate, session: Session = Depends(get_session)) -> dict:
    text = data.text.strip()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    note = {"text": text, "color": "", "at": stamp, "tags": data.tags}

    item = _inbox_item(session)
    block = session.exec(
        select(Block).where(Block.nav_item_id == item.id).order_by(Block.sort_order)
    ).first()
    if block is None:
        raise_api_error(404, "id", "收件箱缺少内容")

    try:
        content = json.loads(block.content or "{}")
    except json.JSONDecodeError:
        content = {}
    if not isinstance(content, dict):
        content = {}
    lines = list(content.get("lines") or [])
    if len(lines) == 1 and not str(lines[0].get("text") or "").strip():
        lines = [note]
    else:
        lines.insert(0, note)
    crud.update_block(
        session,
        block,
        BlockUpdate(content={"mode": content.get("mode") or "numbered", "lines": lines}),
    )
    if data.tags:
        _remember_history(data.tags)
    return {"id": item.id, "group_id": item.group_id, "title": item.title}
