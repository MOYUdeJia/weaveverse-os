"""Appearance settings and background files.

Stored beside the database so themes do not need a table migration.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.config import BACKGROUNDS_DIR, DATA_DIR

SETTINGS_PATH = DATA_DIR / "appearance.json"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_VIDEO_SECONDS = 30
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
THEMES = {"warm", "mint", "sky", "sakura", "ash"}
BARS = {"push", "overlay", "stack"}

DEFAULT = {
    "theme": "warm",
    "bar": "push",
    "player": "bottom",
    "low_power": False,
    "global_image": "",
    "global_video": "",
    "groups": {},
}


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    merged = {**DEFAULT, **data}
    if merged["theme"] not in THEMES:
        merged["theme"] = "warm"
    if merged["bar"] not in BARS:
        merged["bar"] = "push"
    if merged.get("player") not in {"top", "bottom", "corner"}:
        merged["player"] = "bottom"
    merged["low_power"] = bool(merged.get("low_power"))
    groups = merged.get("groups") if isinstance(merged.get("groups"), dict) else {}
    merged["groups"] = {str(key): str(value) for key, value in groups.items() if value}
    return merged


def save_settings(data: dict) -> dict:
    current = load_settings()
    if "theme" in data and data["theme"] in THEMES:
        current["theme"] = data["theme"]
    if "bar" in data and data["bar"] in BARS:
        current["bar"] = data["bar"]
    if data.get("player") in {"top", "bottom", "corner"}:
        current["player"] = data["player"]
    if "low_power" in data:
        current["low_power"] = bool(data["low_power"])
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def store_image(payload: bytes, suffix: str) -> str:
    if len(payload) > MAX_IMAGE_BYTES:
        raise ValueError("图片超过 20MB")
    if suffix not in IMAGE_SUFFIXES:
        raise ValueError("背景只支持 png / jpg / webp / gif")
    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = BACKGROUNDS_DIR / filename
    target.write_bytes(_shrink_image(payload, suffix))
    return filename


def store_video(payload: bytes) -> str:
    if len(payload) > MAX_VIDEO_BYTES:
        raise ValueError("视频超过 50MB")
    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp4"
    target = BACKGROUNDS_DIR / filename
    target.write_bytes(payload)
    seconds = mp4_duration_seconds(target)
    if seconds is None or seconds > MAX_VIDEO_SECONDS:
        target.unlink(missing_ok=True)
        raise ValueError("视频需要能读出时长，并且不超过 30 秒")
    return filename


def assign_file(kind: str, filename: str, group_id: int | None) -> dict:
    settings = load_settings()
    if kind == "video":
        _drop(settings.get("global_video") or "")
        settings["global_video"] = filename
    elif group_id is None:
        _drop(settings.get("global_image") or "")
        settings["global_image"] = filename
    else:
        key = str(group_id)
        _drop(settings["groups"].get(key) or "")
        settings["groups"][key] = filename
    return save_settings(settings)


def clear_file(kind: str, group_id: int | None) -> dict:
    settings = load_settings()
    if kind == "video":
        _drop(settings.get("global_video") or "")
        settings["global_video"] = ""
    elif group_id is None:
        _drop(settings.get("global_image") or "")
        settings["global_image"] = ""
    else:
        key = str(group_id)
        _drop(settings["groups"].pop(key, "") or "")
    return save_settings(settings)


def background_path(filename: str) -> Path:
    name = Path(filename).name
    if name != filename or not name:
        raise ValueError("非法文件名")
    return BACKGROUNDS_DIR / name


def _drop(filename: str) -> None:
    if not filename:
        return
    try:
        path = background_path(filename)
    except ValueError:
        return
    if path.is_file():
        path.unlink()


def _shrink_image(payload: bytes, suffix: str) -> bytes:
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError:
        return payload
    image = Image.open(BytesIO(payload))
    image = image.convert("RGBA" if suffix == ".png" else "RGB")
    if image.width > 2560:
        height = max(1, round(image.height * (2560 / image.width)))
        image = image.resize((2560, height))
    out = BytesIO()
    if suffix in {".jpg", ".jpeg"}:
        image.save(out, format="JPEG", quality=86)
    elif suffix == ".webp":
        image.save(out, format="WEBP", quality=86)
    else:
        image.save(out, format="PNG")
    return out.getvalue()


def mp4_duration_seconds(path: Path) -> float | None:
    data = path.read_bytes()
    index = data.find(b"mvhd")
    if index < 0 or index + 32 > len(data):
        return None
    version = data[index + 4]
    if version == 0:
        timescale = int.from_bytes(data[index + 16 : index + 20], "big")
        duration = int.from_bytes(data[index + 20 : index + 24], "big")
    elif version == 1 and index + 44 <= len(data):
        timescale = int.from_bytes(data[index + 28 : index + 32], "big")
        duration = int.from_bytes(data[index + 32 : index + 40], "big")
    else:
        return None
    if timescale <= 0:
        return None
    return duration / timescale
