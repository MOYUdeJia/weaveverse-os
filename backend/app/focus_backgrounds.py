"""Pictures the fullscreen focus clock can sit on."""

from __future__ import annotations

import re
from pathlib import Path

from app.config import DATA_DIR

_DIR = DATA_DIR / "focus-backgrounds"
_NAME = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
FIELDS = (
    {"id": "ink", "name": "墨", "color": "#16201d"},
    {"id": "leaf", "name": "叶", "color": "#1d3d2e"},
    {"id": "dawn", "name": "纸", "color": "#f4efe7"},
)


def _folder() -> Path:
    _DIR.mkdir(parents=True, exist_ok=True)
    return _DIR


def list_backgrounds() -> list[dict]:
    files = []
    folder = _folder()
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in _TYPES and _NAME.match(path.name):
            files.append({"id": path.name, "name": path.stem, "url": f"/api/focus/backgrounds/{path.name}"})
    return [*FIELDS, *files]


def save_background(filename: str, raw: bytes) -> dict:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in _TYPES:
        raise ValueError("背景只用 png、jpg 或 webp")
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("背景不要超过 8MB")
    folder = _folder()
    stem = re.sub(r"[^A-Za-z0-9_-]", "", Path(filename).stem)[:40] or "picture"
    name = f"{stem}{suffix}"
    target = folder / name
    index = 2
    while target.exists():
        name = f"{stem}-{index}{suffix}"
        target = folder / name
        index += 1
    target.write_bytes(raw)
    return {"id": name, "name": Path(name).stem, "url": f"/api/focus/backgrounds/{name}"}


def read_background(name: str) -> Path | None:
    if not _NAME.match(name or ""):
        return None
    path = _folder() / name
    if path.is_file() and path.suffix.lower() in _TYPES:
        return path
    return None
