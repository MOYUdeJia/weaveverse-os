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


def _quick_tags() -> list[str]:
    try:
        data = json.loads(QUICK_TAGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = list(DEFAULT_QUICK_TAGS)
    if not isinstance(data, list):
        data = list(DEFAULT_QUICK_TAGS)
    cleaned: list[str] = []
    for raw in data:
        text = str(raw).strip().lstrip("#").strip()
        if text and text not in cleaned:
            cleaned.append(text[:24])
    return cleaned[:6] or list(DEFAULT_QUICK_TAGS)


def _write_quick_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in tags:
        text = str(raw).strip().lstrip("#").strip()
        if text and text not in cleaned:
            cleaned.append(text[:24])
    cleaned = cleaned[:6]
    QUICK_TAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUICK_TAGS_PATH.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    return cleaned


@router.get("/tags")
def get_quick_tags() -> dict:
    return {"tags": _quick_tags()}


@router.put("/tags")
def put_quick_tags(data: dict) -> dict:
    tags = data.get("tags") if isinstance(data, dict) else None
    if not isinstance(tags, list):
        raise_api_error(400, "tags", "需要标签数组")
    return {"tags": _write_quick_tags(tags)}


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
    return {"id": item.id, "group_id": item.group_id, "title": item.title}
