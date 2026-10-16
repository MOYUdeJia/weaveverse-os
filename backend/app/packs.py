"""Install and read .wvpack theme archives.

A pack is a zip. Installed copies live in the user themes directory, one folder per id.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from io import BytesIO
from pathlib import Path

from app.config import THEMES_DIR
from app.themes import BUILTIN, parse_theme_bytes

MAX_PACK_BYTES = 80 * 1024 * 1024
MAX_UNPACKED_BYTES = 200 * 1024 * 1024
MAX_FILES = 40
ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-")
ALLOWED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".mp4",
    ".webm",
    ".json",
    ".lottie",
    ".mp3",
    ".wav",
    ".ogg",
}


def _pack_id(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text or len(text) > 40 or text in BUILTIN or any(ch not in ID_CHARS for ch in text):
        raise ValueError("主题包 id 不合法")
    if text.startswith("-") or ".." in text:
        raise ValueError("主题包 id 不合法")
    return text


def pack_dir(pack_id: str) -> Path:
    folder = THEMES_DIR / _pack_id(pack_id)
    return folder


def _relative_file(folder: Path, relative: str) -> Path:
    raw = str(relative or "").replace("\\", "/").lstrip("/")
    if not raw or raw.startswith("../") or "/../" in f"/{raw}":
        raise ValueError("主题包路径不合法")
    path = (folder / raw).resolve()
    root = folder.resolve()
    if path != root and root not in path.parents:
        raise ValueError("主题包路径不合法")
    return path


def list_packs() -> list[dict]:
    if not THEMES_DIR.is_dir():
        return []
    items = []
    for folder in sorted(THEMES_DIR.iterdir()):
        manifest_path = folder / "manifest.json"
        if not folder.is_dir() or not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            pack_id = _pack_id(manifest.get("id") or folder.name)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        preview = str(manifest.get("preview") or "")
        items.append(
            {
                "id": pack_id,
                "name": str(manifest.get("name") or pack_id)[:40],
                "author": str(manifest.get("author") or "")[:40],
                "description": str(manifest.get("description") or "")[:240],
                "preview": preview if preview and (folder / preview).is_file() else "",
            }
        )
    return items


def _theme_from_colors(pack_id: str, name: str, author: str, version: str, payload: bytes) -> dict:
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("colors.json 无法解析") from exc
    if not isinstance(data, dict):
        raise ValueError("colors.json 格式不对")
    if "vars" not in data:
        data = {"vars": data}
    data["format"] = "weaveverse-theme"
    data["spec"] = 1
    data["id"] = pack_id
    data["name"] = name
    data["author"] = author
    data["version"] = version
    theme = parse_theme_bytes(json.dumps(data).encode("utf-8"))
    theme["id"] = pack_id
    return theme


def _splash_spec(raw: object) -> dict:
    from app.appearance import SPLASH_DURATIONS

    if not isinstance(raw, dict):
        return {"type": "", "path": "", "duration": 2, "loop": False}
    kind = raw.get("type") if raw.get("type") in {"image", "video", "lottie"} else ""
    path = str(raw.get("path") or "")
    try:
        duration = int(raw.get("duration") or 2)
    except (TypeError, ValueError):
        duration = 2
    if duration not in SPLASH_DURATIONS:
        duration = 10 if duration > 10 else 2
    return {"type": kind, "path": path, "duration": duration, "loop": bool(raw.get("loop", False))}


def _background_spec(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {"type": "", "path": "", "opacity": None}
    kind = raw.get("type") if raw.get("type") in {"image", "video"} else ""
    path = str(raw.get("path") or "")
    opacity = raw.get("opacity")
    try:
        opacity = float(opacity) if opacity is not None else None
    except (TypeError, ValueError):
        opacity = None
    if opacity is not None:
        opacity = max(0.0, min(1.0, opacity))
    return {"type": kind, "path": path, "opacity": opacity}


def read_pack(pack_id: str) -> dict:
    folder = pack_dir(pack_id)
    manifest_path = folder / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("主题包还没安装")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest.json 格式不对")
    checked = _pack_id(manifest.get("id") or folder.name)
    if checked != folder.name:
        raise ValueError("主题包 id 和目录不一致")
    colors_name = str(manifest.get("colors") or "colors.json")
    colors_path = _relative_file(folder, colors_name)
    if not colors_path.is_file():
        raise ValueError("主题包缺少颜色文件")
    name = str(manifest.get("name") or checked)[:40]
    author = str(manifest.get("author") or "")[:40]
    version = str(manifest.get("version") or "1.0")[:16]
    theme = _theme_from_colors(checked, name, author, version, colors_path.read_bytes())
    splash = _splash_spec(manifest.get("splash"))
    background = _background_spec(manifest.get("background"))
    decorations = manifest.get("decorations") if isinstance(manifest.get("decorations"), list) else []
    sounds = manifest.get("sounds") if isinstance(manifest.get("sounds"), dict) else {}
    return {
        "id": checked,
        "name": name,
        "theme": theme,
        "splash": splash,
        "background": background,
        "decorations": [str(item)[:180] for item in decorations if item][:6],
        "startup_sound": str(sounds.get("startup") or "")[:180],
        "caption": str(manifest.get("caption") or "")[:40],
    }


def install_pack(payload: bytes) -> str:
    if not payload:
        raise ValueError("没有读到主题包")
    if len(payload) > MAX_PACK_BYTES:
        raise ValueError("主题包超过 80MB")
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("主题包不是有效的 zip") from exc
    names = [info.filename for info in archive.infolist() if not info.is_dir()]
    if len(names) > MAX_FILES:
        raise ValueError("主题包文件太多")
    if sum(info.file_size for info in archive.infolist()) > MAX_UNPACKED_BYTES:
        raise ValueError("主题包解压后太大")
    try:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8-sig"))
    except KeyError as exc:
        raise ValueError("主题包缺少 manifest.json") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("manifest.json 无法解析") from exc
    pack_id = _pack_id(manifest.get("id"))
    folder = THEMES_DIR / pack_id
    staging = THEMES_DIR / f".{pack_id}.tmp"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        for info in archive.infolist():
            if info.is_dir():
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix not in ALLOWED_SUFFIXES and Path(info.filename).name != "manifest.json":
                continue
            target = _relative_file(staging, info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
        if not (staging / "manifest.json").is_file():
            raise ValueError("主题包缺少 manifest.json")
        colors_name = str(manifest.get("colors") or "colors.json")
        colors_path = _relative_file(staging, colors_name)
        if not colors_path.is_file():
            raise ValueError("主题包缺少颜色文件")
        _theme_from_colors(
            pack_id,
            str(manifest.get("name") or pack_id)[:40],
            str(manifest.get("author") or "")[:40],
            str(manifest.get("version") or "1.0")[:16],
            colors_path.read_bytes(),
        )
        if folder.exists():
            shutil.rmtree(folder)
        staging.rename(folder)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    read_pack(pack_id)
    return pack_id


def remove_pack(pack_id: str) -> None:
    folder = pack_dir(pack_id)
    if not folder.is_dir():
        raise ValueError("主题包不存在")
    shutil.rmtree(folder)


def pack_file(pack_id: str, relative: str) -> Path:
    folder = pack_dir(pack_id)
    if not folder.is_dir():
        raise ValueError("主题包不存在")
    path = _relative_file(folder, relative)
    if not path.is_file():
        raise ValueError("文件不存在")
    return path
