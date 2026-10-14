"""Store user splash covers next to other user data."""

from __future__ import annotations

import json
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from app.config import SPLASH_DIR

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 80 * 1024 * 1024
MAX_LOTTIE_BYTES = 8 * 1024 * 1024
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_SUFFIXES = {".webm", ".mp4"}
LOTTIE_SUFFIXES = {".json", ".lottie"}


def splash_path(filename: str) -> Path:
    name = Path(filename).name
    if name != filename or not name:
        raise ValueError("非法文件名")
    return SPLASH_DIR / name


def drop_splash(filename: str) -> None:
    if not filename:
        return
    try:
        path = splash_path(filename)
    except ValueError:
        return
    if path.is_file():
        path.unlink()


def _kind_from_suffix(suffix: str) -> str:
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in LOTTIE_SUFFIXES:
        return "lottie"
    raise ValueError("封面支持 png / jpg / gif / webp / webm / mp4 / json / lottie")


def _looks_like_lottie(data: dict) -> bool:
    return isinstance(data.get("layers"), list) and ("v" in data or "fr" in data or "ip" in data)


def _extract_lottie(payload: bytes, suffix: str) -> bytes:
    if suffix == ".json":
        try:
            parsed = json.loads(payload.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Lottie JSON 无法解析") from exc
        if not isinstance(parsed, dict) or not _looks_like_lottie(parsed):
            raise ValueError("这个 JSON 不是 Lottie 动画")
        return json.dumps(parsed, ensure_ascii=False).encode("utf-8")

    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("无法读取 .lottie 文件") from exc
    names = [name for name in archive.namelist() if name.lower().endswith(".json") and not name.endswith("/")]
    if not names:
        raise ValueError(".lottie 里没有动画 JSON")
    preferred = [name for name in names if "/animations/" in name.replace("\\", "/")]
    chosen = preferred[0] if preferred else names[0]
    raw = archive.read(chosen)
    parsed = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(parsed, dict) or not _looks_like_lottie(parsed):
        raise ValueError(".lottie 里的 JSON 不是 Lottie 动画")
    return json.dumps(parsed, ensure_ascii=False).encode("utf-8")


def store_splash(payload: bytes, suffix: str) -> tuple[str, str]:
    if not payload:
        raise ValueError("没有读到文件")
    kind = _kind_from_suffix(suffix)
    if kind == "image" and len(payload) > MAX_IMAGE_BYTES:
        raise ValueError("封面图片超过 20MB")
    if kind == "video" and len(payload) > MAX_VIDEO_BYTES:
        raise ValueError("封面视频超过 80MB")
    if kind == "lottie" and len(payload) > MAX_LOTTIE_BYTES:
        raise ValueError("Lottie 文件超过 8MB")

    SPLASH_DIR.mkdir(parents=True, exist_ok=True)
    if kind == "lottie":
        stored = _extract_lottie(payload, suffix)
        filename = f"{uuid.uuid4().hex}.json"
        (SPLASH_DIR / filename).write_bytes(stored)
        return filename, kind

    filename = f"{uuid.uuid4().hex}{suffix}"
    (SPLASH_DIR / filename).write_bytes(payload)
    return filename, kind
