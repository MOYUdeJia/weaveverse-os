"""Appearance settings and background files.

Stored beside the database so themes do not need a table migration.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from app.config import BACKGROUNDS_DIR, DATA_DIR
from app.splash import drop_splash
from app.themes import BUILTIN, drop_custom, find_custom, upsert_custom

SETTINGS_PATH = DATA_DIR / "appearance.json"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_VIDEO_SECONDS = 30
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
THEMES = set(BUILTIN)
BARS = {"push", "overlay", "stack"}
PLAYERS = {"bottom", "corner", "side", "free"}
SPREADS = {"auto", "side", "center"}
PROGRESS_STYLES = {"solid", "gradient"}
SPLASH_MODES = {"default", "image", "video", "lottie"}
SPLASH_DURATIONS = {2, 3, 5, 10, 14}
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

DEFAULT = {
    "theme": "warm",
    "bar": "push",
    "player": "corner",
    "player_hidden": False,
    "player_x": None,
    "player_y": None,
    "player_spread": "auto",
    "progress_style": "solid",
    "progress_color": "#3f6f57",
    "low_power": False,
    "bg_opacity": 0.85,
    "hide_guide": False,
    "splash_mode": "default",
    "splash_file": "",
    "splash_name": "",
    "splash_owner": "",
    "splash_caption": "正在编织你的宇宙",
    "splash_duration": 2,
    "splash_loop": True,
    "active_pack": "",
    "pack_background_kind": "",
    "pack_background": "",
    "pack_caption": "",
    "decorations": [],
    "startup_sound": "",
    "custom_themes": [],
    "global_image": "",
    "global_video": "",
    "global_image_name": "",
    "global_video_name": "",
    "groups": {},
    "group_names": {},
    "current_preset": "",
    "slots": {"colors": "warm", "background": None, "splash": None, "icons": None},
    "slot_config": {"splash": {"duration": 2, "slogan": ""}},
    "dirty": False,
    "library_ready": False,
    "slot_background": "",
    "slot_background_media": "",
}


def _slots(raw: object) -> dict:
    source = raw if isinstance(raw, dict) else {}
    slots = {}
    for key in ("colors", "background", "splash", "icons"):
        value = source.get(key)
        text = str(value or "").strip()
        if key == "colors":
            slots[key] = text[:40] or "warm"
        elif text in {"", "default", "none"}:
            slots[key] = None
        else:
            slots[key] = text[:40]
    return slots


def _icon_bindings(raw: object) -> dict:
    """Per-preset map of nav and group ids to icons. Missing maps stay empty."""
    source = raw if isinstance(raw, dict) else {}
    cleaned = {"nav": {}, "group": {}}
    for kind in ("nav", "group"):
        bucket = source.get(kind)
        if not isinstance(bucket, dict):
            continue
        for key, value in list(bucket.items())[:240]:
            ident = str(key).strip()
            text = str(value or "").strip()
            if not ident.isdigit() or not text or len(text) > 20:
                continue
            cleaned[kind][ident] = text
    return cleaned


def _slot_config(raw: object) -> dict:
    source = raw if isinstance(raw, dict) else {}
    splash = source.get("splash") if isinstance(source.get("splash"), dict) else {}
    try:
        duration = int(splash.get("duration") or 2)
    except (TypeError, ValueError):
        duration = 2
    if duration not in SPLASH_DURATIONS:
        duration = 2
    return {
        "splash": {"duration": duration, "slogan": str(splash.get("slogan") or "")[:40]},
        "icon_bindings": _icon_bindings(source.get("icon_bindings")),
    }


def _ratio(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return max(0.0, min(1.0, number))


def load_settings() -> dict:
    from app.library import ensure_library

    ensure_library()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    merged = {**DEFAULT, **data}
    if merged["bar"] not in BARS:
        merged["bar"] = "push"
    player = merged.get("player")
    if player == "top":
        player = "side"
    if player not in PLAYERS:
        player = "corner"
    merged["player"] = player
    merged["player_hidden"] = bool(merged.get("player_hidden"))
    merged["player_x"] = _ratio(merged.get("player_x"))
    merged["player_y"] = _ratio(merged.get("player_y"))
    if merged["player"] == "free" and (merged["player_x"] is None or merged["player_y"] is None):
        merged["player"] = "corner"
    spread = merged.get("player_spread") or "auto"
    merged["player_spread"] = spread if spread in SPREADS else "auto"
    style = merged.get("progress_style")
    merged["progress_style"] = style if style in PROGRESS_STYLES else "solid"
    color = str(merged.get("progress_color") or "")
    merged["progress_color"] = color.lower() if COLOR_PATTERN.fullmatch(color) else "#3f6f57"
    merged["low_power"] = bool(merged.get("low_power"))
    opacity = _ratio(merged.get("bg_opacity"))
    merged["bg_opacity"] = 0.85 if opacity is None else opacity
    merged["hide_guide"] = bool(merged.get("hide_guide"))
    mode = merged.get("splash_mode") or "default"
    merged["splash_mode"] = mode if mode in SPLASH_MODES else "default"
    merged["splash_file"] = str(merged.get("splash_file") or "")
    merged["splash_name"] = str(merged.get("splash_name") or "")[:120]
    owner = merged.get("splash_owner") or ""
    merged["splash_owner"] = owner if owner in {"user", "pack"} else ""
    merged["splash_caption"] = str(merged.get("splash_caption") or "正在编织你的宇宙")[:40]
    merged["active_pack"] = str(merged.get("active_pack") or "")[:40]
    kind = merged.get("pack_background_kind") or ""
    merged["pack_background_kind"] = kind if kind in {"image", "video"} else ""
    merged["pack_background"] = str(merged.get("pack_background") or "")[:180]
    merged["pack_caption"] = str(merged.get("pack_caption") or "")[:40]
    decorations = merged.get("decorations") if isinstance(merged.get("decorations"), list) else []
    merged["decorations"] = [str(item)[:180] for item in decorations if item][:6]
    merged["startup_sound"] = str(merged.get("startup_sound") or "")[:180]
    try:
        duration = int(merged.get("splash_duration") or 2)
    except (TypeError, ValueError):
        duration = 2
    merged["splash_duration"] = duration if duration in SPLASH_DURATIONS else 2
    merged["splash_loop"] = bool(merged.get("splash_loop") if merged.get("splash_loop") is not None else True)
    custom = merged.get("custom_themes") if isinstance(merged.get("custom_themes"), list) else []
    merged["custom_themes"] = [item for item in custom if isinstance(item, dict) and item.get("id")]
    if merged["theme"] not in THEMES and not find_custom(merged["custom_themes"], merged["theme"]):
        merged["theme"] = "warm"
    groups = merged.get("groups") if isinstance(merged.get("groups"), dict) else {}
    merged["groups"] = {str(key): str(value) for key, value in groups.items() if value}
    names = merged.get("group_names") if isinstance(merged.get("group_names"), dict) else {}
    merged["group_names"] = {str(key): str(value)[:120] for key, value in names.items() if value}
    merged["global_image_name"] = str(merged.get("global_image_name") or "")[:120]
    merged["global_video_name"] = str(merged.get("global_video_name") or "")[:120]
    merged["current_preset"] = str(merged.get("current_preset") or "")[:40]
    merged["dirty"] = bool(merged.get("dirty"))
    merged["library_ready"] = bool(merged.get("library_ready"))
    merged["slot_background"] = str(merged.get("slot_background") or "")[:40]
    media = merged.get("slot_background_media") or ""
    merged["slot_background_media"] = media if media in {"image", "video"} else ""
    merged["slots"] = _slots(merged.get("slots"))
    merged["slot_config"] = _slot_config(merged.get("slot_config"))
    from app.packs import list_packs

    merged["packs"] = list_packs()
    return merged


def _write(settings: dict) -> dict:
    stored = {key: value for key, value in settings.items() if key != "packs"}
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
    stored["packs"] = settings.get("packs") if isinstance(settings.get("packs"), list) else []
    from app.packs import list_packs

    stored["packs"] = list_packs()
    return stored


def save_settings(data: dict) -> dict:
    current = load_settings()
    if "theme" in data:
        theme_id = str(data["theme"] or "")
        if theme_id in THEMES or find_custom(current["custom_themes"], theme_id):
            current["theme"] = theme_id
            if current.get("active_pack") and theme_id != current["active_pack"]:
                _clear_pack_visuals(current)
    if "bar" in data and data["bar"] in BARS:
        current["bar"] = data["bar"]
    if data.get("player") in {"bottom", "corner", "side"}:
        current["player"] = data["player"]
        current["player_x"] = None
        current["player_y"] = None
    elif data.get("player") == "free":
        current["player"] = "free"
    if "player_x" in data:
        current["player_x"] = _ratio(data.get("player_x"))
    if "player_y" in data:
        current["player_y"] = _ratio(data.get("player_y"))
    if data.get("player_spread") in SPREADS:
        current["player_spread"] = data["player_spread"]
    if "player_hidden" in data:
        current["player_hidden"] = bool(data.get("player_hidden"))
    if data.get("progress_style") in PROGRESS_STYLES:
        current["progress_style"] = data["progress_style"]
    if "progress_color" in data:
        color = str(data.get("progress_color") or "")
        if COLOR_PATTERN.fullmatch(color):
            current["progress_color"] = color.lower()
    if "low_power" in data:
        current["low_power"] = bool(data["low_power"])
    if "bg_opacity" in data:
        opacity = _ratio(data.get("bg_opacity"))
        if opacity is not None:
            current["bg_opacity"] = opacity
    if "hide_guide" in data:
        current["hide_guide"] = bool(data["hide_guide"])
    if data.get("splash_mode") in SPLASH_MODES:
        current["splash_mode"] = data["splash_mode"]
        if current["splash_mode"] == "default":
            if current.get("splash_owner") != "pack":
                drop_splash(current.get("splash_file") or "")
            current["splash_file"] = ""
            current["splash_name"] = ""
            current["splash_owner"] = ""
    if "splash_caption" in data:
        current["splash_caption"] = str(data.get("splash_caption") or "正在编织你的宇宙")[:40]
    if "splash_duration" in data:
        try:
            duration = int(data.get("splash_duration"))
        except (TypeError, ValueError):
            duration = current["splash_duration"]
        if duration in SPLASH_DURATIONS:
            current["splash_duration"] = duration
    if "splash_loop" in data:
        current["splash_loop"] = bool(data["splash_loop"])
    return _write(current)


def assign_splash(filename: str, kind: str, label: str = "") -> dict:
    settings = load_settings()
    drop_splash(settings.get("splash_file") or "")
    settings["splash_file"] = filename
    settings["splash_name"] = (label or filename)[:120]
    settings["splash_mode"] = kind if kind in SPLASH_MODES else "image"
    settings["splash_owner"] = "user"
    return _write(settings)


def clear_splash() -> dict:
    settings = load_settings()
    drop_splash(settings.get("splash_file") or "")
    settings["splash_file"] = ""
    settings["splash_name"] = ""
    settings["splash_mode"] = "default"
    settings["splash_owner"] = ""
    return _write(settings)


def _clear_pack_visuals(current: dict) -> None:
    if current.get("splash_owner") == "pack":
        current["splash_mode"] = "default"
        current["splash_file"] = ""
        current["splash_name"] = ""
        current["splash_owner"] = ""
    current["active_pack"] = ""
    current["pack_background_kind"] = ""
    current["pack_background"] = ""
    current["pack_caption"] = ""
    current["decorations"] = []
    current["startup_sound"] = ""


def activate_pack(pack_id: str) -> dict:
    from app.packs import read_pack

    pack = read_pack(pack_id)
    settings = load_settings()
    settings["custom_themes"] = upsert_custom(settings["custom_themes"], pack["theme"])
    settings["theme"] = pack["theme"]["id"]
    settings["active_pack"] = pack["id"]
    splash = pack["splash"]
    if splash["path"]:
        settings["splash_mode"] = splash["type"]
        settings["splash_file"] = splash["path"]
        settings["splash_name"] = pack["name"]
        settings["splash_owner"] = "pack"
        settings["splash_duration"] = splash["duration"]
        settings["splash_loop"] = splash["loop"]
    settings["pack_background_kind"] = pack["background"]["type"]
    settings["pack_background"] = pack["background"]["path"]
    if pack["background"]["opacity"] is not None:
        settings["bg_opacity"] = pack["background"]["opacity"]
    settings["decorations"] = pack["decorations"]
    settings["startup_sound"] = pack["startup_sound"]
    settings["pack_caption"] = pack["caption"]
    return _write(settings)


def delete_pack(pack_id: str) -> dict:
    from app.packs import remove_pack

    remove_pack(pack_id)
    settings = load_settings()
    settings["custom_themes"] = drop_custom(settings["custom_themes"], pack_id)
    if settings.get("active_pack") == pack_id or settings.get("theme") == pack_id:
        _clear_pack_visuals(settings)
        if settings.get("theme") == pack_id:
            settings["theme"] = "warm"
    return _write(settings)


def import_theme(theme: dict) -> dict:
    settings = load_settings()
    settings["custom_themes"] = upsert_custom(settings["custom_themes"], theme)
    settings["theme"] = theme["id"]
    return _write(settings)


def remove_theme(theme_id: str) -> dict:
    settings = load_settings()
    if theme_id in THEMES:
        raise ValueError("预设主题不能删除")
    settings["custom_themes"] = drop_custom(settings["custom_themes"], theme_id)
    if settings["theme"] == theme_id:
        settings["theme"] = "warm"
    return _write(settings)


def store_image(payload: bytes, suffix: str) -> str:
    if not payload:
        raise ValueError("没有读到文件")
    if len(payload) > MAX_IMAGE_BYTES:
        raise ValueError("图片超过 20MB")
    if suffix not in IMAGE_SUFFIXES:
        raise ValueError("背景只支持 png / jpg / webp / gif")
    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = BACKGROUNDS_DIR / filename
    # 动图原样保存。重新编码会丢掉动画，扩展名也对不上。
    if suffix == ".gif":
        target.write_bytes(payload)
        return filename
    try:
        stored = _shrink_image(payload, suffix)
    except OSError as exc:
        raise ValueError("这张图片无法读取") from exc
    target.write_bytes(stored)
    return filename


def store_video(payload: bytes) -> str:
    if not payload:
        raise ValueError("没有读到文件")
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


def assign_file(kind: str, filename: str, group_id: int | None, label: str = "") -> dict:
    settings = load_settings()
    shown = (label or filename)[:120]
    if kind == "video":
        _drop(settings.get("global_video") or "")
        settings["global_video"] = filename
        settings["global_video_name"] = shown
    elif group_id is None:
        _drop(settings.get("global_image") or "")
        settings["global_image"] = filename
        settings["global_image_name"] = shown
    else:
        key = str(group_id)
        _drop(settings["groups"].get(key) or "")
        settings["groups"][key] = filename
        settings["group_names"][key] = shown
    return _write(settings)


def clear_file(kind: str, group_id: int | None) -> dict:
    settings = load_settings()
    if kind == "video":
        _drop(settings.get("global_video") or "")
        settings["global_video"] = ""
        settings["global_video_name"] = ""
    elif group_id is None:
        _drop(settings.get("global_image") or "")
        settings["global_image"] = ""
        settings["global_image_name"] = ""
    else:
        key = str(group_id)
        _drop(settings["groups"].pop(key, "") or "")
        settings["group_names"].pop(key, None)
    return _write(settings)


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
