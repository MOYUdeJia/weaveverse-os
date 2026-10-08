"""Store cropped navigation icons and resolve @file: references.

Plain emoji icons stay as text. An uploaded icon is `@file:` plus 12 hex
characters, which fits the existing 20-character icon field.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from sqlmodel import Session, select

from app.config import ICONS_DIR
from app.models import Group, NavItem


ICON_PREFIX = "@file:"
ICON_PATTERN = re.compile(r"@file:([0-9a-f]{12})\Z")
MAX_ICON_BYTES = 512 * 1024


# 从 icon 字段取出文件编号。普通 emoji 返回空。
# Pull the file id out of an icon field. Plain emoji returns nothing.
def icon_file_id(icon: str) -> str | None:
    match = ICON_PATTERN.fullmatch(icon or "")
    return match.group(1) if match else None


def icon_reference(icon_id: str) -> str:
    return f"{ICON_PREFIX}{icon_id}"


def icon_path(icon_id: str) -> Path:
    return ICONS_DIR / f"{icon_id}.png"


# 保存裁剪后的 PNG，返回可写入 nav_items.icon 的引用。
# Save a cropped PNG and return the reference stored in nav_items.icon.
def save_icon_png(payload: bytes) -> str:
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("只接受 PNG")
    if len(payload) > MAX_ICON_BYTES:
        raise ValueError("图标超过 512KB")

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        icon_id = uuid.uuid4().hex[:12]
        target = icon_path(icon_id)
        if target.exists():
            continue
        target.write_bytes(payload)
        return icon_reference(icon_id)
    raise ValueError("无法保存图标")


# 没有导航或分组再引用这张图时，删掉文件。
# Delete the file once no navigation item or group still points at it.
def release_icon(session: Session, icon: str) -> None:
    icon_id = icon_file_id(icon)
    if icon_id is None:
        return
    still_used = session.exec(select(NavItem.id).where(NavItem.icon == icon)).first()
    if still_used is None:
        still_used = session.exec(select(Group.id).where(Group.icon == icon)).first()
    if still_used is not None:
        return
    path = icon_path(icon_id)
    if path.is_file():
        path.unlink()


# 按编号删未保存的图标。仍被导航使用时拒绝。
# Delete an unsaved icon by id. Refuse when a navigation item still uses it.
def delete_icon_id(session: Session, icon_id: str) -> None:
    if re.fullmatch(r"[0-9a-f]{12}", icon_id) is None:
        raise ValueError("图标引用无效")
    release_icon(session, icon_reference(icon_id))
