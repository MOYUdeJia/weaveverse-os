"""Asset library, preset snapshots, and the four live slots.

Colors, backgrounds, splashes, and icon packs are separate assets.
A preset stores which asset each slot uses. Opacity, bar style, and the
player position stay in appearance settings and are not part of a preset.
"""

from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from app.config import ASSETS_DIR, BACKGROUNDS_DIR, DATA_DIR, PRESETS_DIR, SPLASH_DIR, THEMES_DIR
from app.themes import BUILTIN, export_payload, parse_theme_bytes

ASSET_TYPES = ("colors", "backgrounds", "splashes", "icons")
SLOT_KEYS = ("colors", "background", "splash", "icons")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_SUFFIXES = {".webm", ".mp4"}
LOTTIE_SUFFIXES = {".json", ".lottie"}
INDEX_PATH = ASSETS_DIR / "assets.json"
PRESET_INDEX = PRESETS_DIR / "presets.json"
MAX_MEDIA_BYTES = 80 * 1024 * 1024
SKIP_MEDIA_NAMES = {"startup.mp4"}

_ready = False
_ensuring = False


def _read_json(path: Path, fallback: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    return data if isinstance(data, dict) else fallback


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _empty_index() -> dict:
    return {"version": 1, "colors": [], "backgrounds": [], "splashes": [], "icons": []}


def load_index() -> dict:
    index = _empty_index()
    index.update(_read_json(INDEX_PATH, {}))
    for key in ASSET_TYPES:
        items = index.get(key)
        index[key] = [item for item in items if isinstance(item, dict) and item.get("id")] if isinstance(items, list) else []
    index["version"] = 1
    return index


def _save_index(index: dict) -> dict:
    stored = {"version": 1, **{key: index.get(key) or [] for key in ASSET_TYPES}}
    _write_json(INDEX_PATH, stored)
    return stored


def _preset_path(preset_id: str) -> Path:
    return PRESETS_DIR / f"{preset_id}.json"


def list_presets() -> list[dict]:
    order = _read_json(PRESET_INDEX, {"order": []}).get("order") or []
    found = {}
    if PRESETS_DIR.is_dir():
        for path in PRESETS_DIR.glob("*.json"):
            if path.name == "presets.json":
                continue
            data = _read_json(path, {})
            if data.get("id"):
                found[data["id"]] = _clean_preset(data)
    items = [found[item] for item in order if item in found]
    items.extend(found[item] for item in found if item not in order)
    system = [item for item in items if item.get("system")]
    custom = [item for item in items if not item.get("system")]
    return system + custom


def get_preset(preset_id: str) -> dict | None:
    for item in list_presets():
        if item["id"] == preset_id:
            return item
    return None


def _clean_preset(raw: dict) -> dict:
    from app.appearance import _slot_config, _slots

    preset_id = str(raw.get("id") or "")[:40]
    slots = _slots(raw.get("slots"))
    if not slots["colors"]:
        slots["colors"] = "warm"
    return {
        "id": preset_id,
        "name": str(raw.get("name") or preset_id)[:40],
        "author": str(raw.get("author") or "")[:40],
        "system": bool(raw.get("system")),
        "based_on": str(raw.get("based_on") or "")[:40] or None,
        "slots": slots,
        "slot_config": _slot_config(raw.get("slot_config")),
    }


def _save_preset(preset: dict) -> dict:
    cleaned = _clean_preset(preset)
    _write_json(_preset_path(cleaned["id"]), cleaned)
    order = [item["id"] for item in list_presets()]
    if cleaned["id"] not in order:
        order.append(cleaned["id"])
    _write_json(PRESET_INDEX, {"version": 1, "order": order})
    return cleaned


def _safe_asset_path(relative: str) -> Path:
    raw = str(relative or "").replace("\\", "/").lstrip("/")
    path = (ASSETS_DIR / raw).resolve()
    root = ASSETS_DIR.resolve()
    if path != root and root not in path.parents:
        raise ValueError("素材路径不合法")
    return path


def _palette_vars(item: dict) -> dict:
    from app.themes import BUILTIN

    asset_id = str(item.get("id") or "")
    if asset_id in BUILTIN:
        return dict(BUILTIN[asset_id]["vars"])
    try:
        payload = json.loads(_safe_asset_path(item["path"]).read_text(encoding="utf-8"))
        vars_ = payload.get("vars") or {}
    except (OSError, json.JSONDecodeError, ValueError, KeyError):
        vars_ = {}
    return vars_ if isinstance(vars_, dict) else {}


def _palette_preview(item: dict) -> dict:
    vars_ = _palette_vars(item)

    def pick(key: str, fallback: str) -> str:
        value = str(vars_.get(key) or "").strip()
        if value.startswith("#") or value.startswith("rgb"):
            return value
        return fallback

    return {
        "dawn": pick("dawn", "#f4efe7"),
        "nav": pick("nav", "#f8f5ee"),
        "progress": pick("progress", "#3f6f57"),
    }


def _present_asset(asset_type: str, item: dict) -> dict:
    shown = dict(item)
    if shown.get("media") == "palette":
        preview = _palette_preview(shown)
        shown["palette"] = preview
        shown["swatch"] = preview["progress"]
    if asset_type == "icons":
        try:
            names = list_icon_entries(shown["id"])
        except (ValueError, OSError):
            names = []
        if names:
            shown["preview"] = names[0]
    return shown


def list_assets(asset_type: str | None = None) -> dict:
    index = load_index()
    shown = {key: [_present_asset(key, item) for item in index.get(key, [])] for key in ASSET_TYPES}
    if asset_type is None:
        return {"version": index.get("version", 1), **shown}
    if asset_type not in ASSET_TYPES:
        raise ValueError("没有这种素材")
    return {asset_type: shown[asset_type]}


def icon_entry(asset_id: str, name: str) -> Path:
    folder = asset_file("icons", asset_id)
    target = (folder / Path(name).name).resolve()
    root = folder.resolve()
    if target.parent != root or not target.is_file():
        raise ValueError("图标不存在")
    if target.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("图标不存在")
    return target


def list_icon_entries(asset_id: str) -> list[str]:
    folder = asset_file("icons", asset_id)
    if folder.is_file():
        return [folder.name] if folder.suffix.lower() in IMAGE_SUFFIXES else []
    return sorted(path.name for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)


def asset_file(asset_type: str, asset_id: str) -> Path:
    item = _find_asset(asset_type, asset_id)
    if item is None:
        raise ValueError("素材不存在")
    path = _safe_asset_path(item["path"])
    if not path.exists():
        raise ValueError("素材文件不存在")
    return path


def _find_asset(asset_type: str, asset_id: str) -> dict | None:
    for item in load_index().get(asset_type, []):
        if item.get("id") == asset_id:
            return item
    return None


def _add_asset(asset_type: str, item: dict) -> dict:
    index = load_index()
    index[asset_type] = [asset for asset in index[asset_type] if asset.get("id") != item["id"]]
    index[asset_type].append(item)
    _save_index(index)
    return item


def _media_kind(asset_type: str, suffix: str) -> str:
    if asset_type == "colors":
        return "palette"
    if asset_type == "icons":
        return "pack"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in LOTTIE_SUFFIXES:
        return "lottie"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    raise ValueError("这个文件不能放进该素材类型")


def store_icon_images(files: list[tuple[str, bytes]], name: str = "") -> dict:
    asset_id = f"u-{uuid.uuid4().hex[:10]}"
    folder = _safe_asset_path(f"icons/{asset_id}")
    folder.mkdir(parents=True, exist_ok=True)
    count = 0
    for filename, payload in files:
        suffix = Path(filename or "").suffix.lower()
        if suffix not in IMAGE_SUFFIXES or not payload or len(payload) > MAX_MEDIA_BYTES:
            continue
        (folder / f"{count:02d}-{Path(filename).stem[:24]}{suffix}").write_bytes(payload)
        count += 1
    if count == 0:
        shutil.rmtree(folder, ignore_errors=True)
        raise ValueError("图标包里没有 png / jpg / webp / gif")
    return _add_asset("icons", {
        "id": asset_id,
        "name": (name or "图标包")[:40],
        "system": False,
        "path": f"icons/{asset_id}",
        "media": "pack",
        "count": count,
    })


def store_upload(asset_type: str, filename: str, payload: bytes, name: str = "") -> dict:
    if asset_type not in ASSET_TYPES:
        raise ValueError("没有这种素材")
    if not payload:
        raise ValueError("没有读到文件")
    if len(payload) > MAX_MEDIA_BYTES:
        raise ValueError("素材超过 80MB")
    suffix = Path(filename or "").suffix.lower()
    if asset_type == "colors":
        theme = parse_theme_bytes(payload)
        return _store_color(theme, system=False, name=name or theme["name"])
    if asset_type == "icons" and suffix == ".zip":
        return _store_icon_zip(payload, name or Path(filename).stem)
    kind = _media_kind(asset_type, suffix)
    if asset_type == "backgrounds" and kind not in {"image", "video"}:
        raise ValueError("背景只接受图片或视频")
    if asset_type == "splashes" and kind not in {"image", "video", "lottie"}:
        raise ValueError("开屏只接受图片、视频或 Lottie")
    asset_id = f"u-{uuid.uuid4().hex[:10]}"
    relative = f"user/{asset_id}{suffix}"
    target = _safe_asset_path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return _add_asset(asset_type, {
        "id": asset_id,
        "name": (name or Path(filename).stem or asset_id)[:40],
        "system": False,
        "path": relative,
        "media": kind,
    })


def _store_color(theme: dict, system: bool, name: str = "") -> dict:
    asset_id = theme["id"] if system else theme["id"]
    if not system and _find_asset("colors", asset_id) and asset_id in BUILTIN:
        asset_id = f"c-{theme['id']}"
    relative = f"colors/{asset_id}.json"
    payload = export_payload(asset_id, name or theme["name"], theme.get("author") or "", theme.get("version") or "1.0.0", theme["vars"])
    _write_json(_safe_asset_path(relative), payload)
    return _add_asset("colors", {
        "id": asset_id,
        "name": (name or theme["name"])[:40],
        "system": system,
        "path": relative,
        "media": "palette",
    })


def _store_icon_zip(payload: bytes, name: str) -> dict:
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("图标包不是有效的 zip") from exc
    asset_id = f"u-{uuid.uuid4().hex[:10]}"
    folder = _safe_asset_path(f"icons/{asset_id}")
    folder.mkdir(parents=True, exist_ok=True)
    count = 0
    for info in archive.infolist():
        if info.is_dir():
            continue
        suffix = Path(info.filename).suffix.lower()
        if suffix not in IMAGE_SUFFIXES or Path(info.filename).name in SKIP_MEDIA_NAMES:
            continue
        target = folder / Path(info.filename).name
        if target.parent != folder:
            continue
        target.write_bytes(archive.read(info))
        count += 1
    if count == 0:
        shutil.rmtree(folder, ignore_errors=True)
        raise ValueError("图标包里没有 png / jpg / webp / gif")
    return _add_asset("icons", {
        "id": asset_id,
        "name": name[:40] or asset_id,
        "system": False,
        "path": f"icons/{asset_id}",
        "media": "pack",
        "count": count,
    })


def delete_asset(asset_type: str, asset_id: str) -> None:
    item = _find_asset(asset_type, asset_id)
    if item is None:
        raise ValueError("素材不存在")
    if item.get("system"):
        raise ValueError("系统素材不能删除")
    path = _safe_asset_path(item["path"])
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()
    index = load_index()
    index[asset_type] = [asset for asset in index[asset_type] if asset.get("id") != asset_id]
    _save_index(index)


def create_preset(name: str, slots: dict | None = None, slot_config: dict | None = None, based_on: str | None = None, inherit_base: bool = True) -> dict:
    from app.appearance import load_settings

    current = load_settings()
    base = (based_on or current.get("current_preset") or None) if inherit_base else based_on
    preset = _clean_preset({
        "id": f"p-{uuid.uuid4().hex[:8]}",
        "name": name or "未命名预设",
        "author": "用户",
        "system": False,
        "based_on": base,
        "slots": slots or current.get("slots"),
        "slot_config": slot_config or current.get("slot_config"),
    })
    return _save_preset(preset)


def update_preset(preset_id: str, data: dict) -> dict:
    current = get_preset(preset_id)
    if current is None:
        raise ValueError("预设不存在")
    if current["system"]:
        raise ValueError("系统预设不能修改，请另存为")
    if "name" in data:
        current["name"] = str(data.get("name") or current["name"])[:40]
    if "slots" in data:
        current["slots"] = data["slots"]
    if "slot_config" in data:
        current["slot_config"] = data["slot_config"]
    return _save_preset(current)


def delete_preset(preset_id: str) -> None:
    current = get_preset(preset_id)
    if current is None:
        raise ValueError("预设不存在")
    if current["system"]:
        raise ValueError("系统预设不能删除")
    _preset_path(preset_id).unlink(missing_ok=True)
    order = [item["id"] for item in list_presets()]
    _write_json(PRESET_INDEX, {"version": 1, "order": order})


def _appearance_raw() -> dict:
    from app.appearance import SETTINGS_PATH, load_settings

    if not SETTINGS_PATH.exists():
        return load_settings()
    return load_settings()


def _write_appearance(settings: dict) -> dict:
    from app.appearance import _write

    return _write(settings)


def slot_state() -> dict:
    from app.appearance import load_settings

    current = load_settings()
    preset = get_preset(current.get("current_preset") or "")
    return {
        "current_preset": current.get("current_preset") or "",
        "current_preset_system": bool(preset and preset["system"]),
        "slots": current["slots"],
        "slot_config": current["slot_config"],
        "dirty": bool(current.get("dirty")),
    }


def _same_slots(left: dict, right: dict, left_config: dict, right_config: dict) -> bool:
    return left == right and left_config == right_config


def patch_slots(data: dict) -> dict:
    from app.appearance import _slot_config, _slots, load_settings

    current = load_settings()
    slots = dict(current["slots"])
    for key in SLOT_KEYS:
        if key in data:
            slots[key] = data[key]
    slots = _slots(slots)
    if slots["colors"] and _find_asset("colors", slots["colors"]) is None and slots["colors"] not in BUILTIN:
        raise ValueError("没有这套颜色")
    for key, asset_type in (("background", "backgrounds"), ("splash", "splashes"), ("icons", "icons")):
        if slots[key] and _find_asset(asset_type, slots[key]) is None:
            raise ValueError("没有这个素材")
    config = _slot_config(data.get("slot_config") or current.get("slot_config"))
    preset = get_preset(current.get("current_preset") or "")
    dirty = True
    if preset and _same_slots(slots, preset["slots"], config, preset["slot_config"]):
        dirty = False
    current["slots"] = slots
    current["slot_config"] = config
    current["dirty"] = dirty
    scope = {key for key in SLOT_KEYS if key in data}
    if "slot_config" in data:
        scope.add("splash")
    _apply_slots(current, scope or set(SLOT_KEYS))
    return slot_state()


def _apply_slots(settings: dict, scope: set[str] | None = None) -> dict:
    """Push the live slots into the fields the current window already reads."""
    from app.themes import find_custom

    touched = set(SLOT_KEYS) if scope is None else scope
    if "colors" in touched:
        color_id = settings["slots"]["colors"] or "warm"
        settings["theme"] = color_id if color_id in BUILTIN or find_custom(settings.get("custom_themes") or [], color_id) else settings.get("theme") or "warm"
        if color_id not in BUILTIN:
            record = _find_asset("colors", color_id)
            if record:
                try:
                    theme = parse_theme_bytes(_safe_asset_path(record["path"]).read_bytes())
                    from app.themes import upsert_custom

                    settings["custom_themes"] = upsert_custom(settings.get("custom_themes") or [], theme)
                    settings["theme"] = theme["id"]
                except (OSError, ValueError):
                    pass
    if "splash" in touched:
        splash_id = settings["slots"].get("splash")
        if not splash_id:
            settings["splash_mode"] = "default"
            settings["splash_file"] = ""
            settings["splash_name"] = ""
            settings["splash_owner"] = ""
        else:
            record = _find_asset("splashes", splash_id)
            if record:
                settings["splash_mode"] = record.get("media") if record.get("media") in {"image", "video", "lottie"} else "image"
                settings["splash_file"] = splash_id
                settings["splash_name"] = record.get("name") or splash_id
                settings["splash_owner"] = "slot"
                settings["splash_duration"] = settings["slot_config"]["splash"]["duration"]
                slogan = settings["slot_config"]["splash"]["slogan"]
                if slogan:
                    settings["splash_caption"] = slogan
    if "background" in touched:
        background_id = settings["slots"].get("background") or ""
        record = _find_asset("backgrounds", background_id) if background_id else None
        settings["slot_background"] = background_id
        settings["slot_background_media"] = record.get("media") if record else ""
    return _write_appearance(settings)


def apply_preset(preset_id: str, resolution: str = "", save_name: str = "") -> dict:
    from app.appearance import load_settings

    preset = get_preset(preset_id)
    if preset is None:
        raise ValueError("预设不存在")
    current = load_settings()
    if current.get("dirty") and resolution not in {"save", "save_as", "discard"}:
        active = get_preset(current.get("current_preset") or "")
        raise DirtyPreset(bool(active and not active["system"]))
    if current.get("dirty") and resolution == "save":
        active = get_preset(current.get("current_preset") or "")
        if active is None or active["system"]:
            raise ValueError("系统预设不能覆盖，请另存为")
        saved = update_preset(active["id"], {"slots": current["slots"], "slot_config": current["slot_config"]})
        if saved["id"] == preset["id"]:
            preset = saved
    if current.get("dirty") and resolution == "save_as":
        create_preset(save_name or "未命名预设", current["slots"], current["slot_config"], current.get("current_preset") or None)
    warnings = _missing_slot_assets(preset["slots"])
    current["current_preset"] = preset["id"]
    current["slots"] = preset["slots"]
    current["slot_config"] = preset["slot_config"]
    current["dirty"] = False
    _apply_slots(current)
    state = slot_state()
    state["warnings"] = warnings
    return state


def _missing_slot_assets(slots: dict) -> list[str]:
    missing = []
    if slots.get("colors") and slots["colors"] not in BUILTIN and _find_asset("colors", slots["colors"]) is None:
        missing.append("colors")
        slots["colors"] = "warm"
    for key, asset_type in (("background", "backgrounds"), ("splash", "splashes"), ("icons", "icons")):
        if slots.get(key) and _find_asset(asset_type, slots[key]) is None:
            missing.append(key)
            slots[key] = None
    return missing


class DirtyPreset(ValueError):
    def __init__(self, can_save: bool) -> None:
        super().__init__("当前配置有未保存修改")
        self.can_save = can_save


def export_preset(preset_id: str) -> tuple[bytes, str]:
    preset = get_preset(preset_id)
    if preset is None:
        raise ValueError("预设不存在")
    buffer = BytesIO()
    manifest = {
        "format": "weaveverse-preset",
        "spec": 2,
        "preset": preset,
        "system_refs": [],
        "files": [],
    }
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key, asset_type in (("colors", "colors"), ("background", "backgrounds"), ("splash", "splashes"), ("icons", "icons")):
            asset_id = preset["slots"].get(key)
            if not asset_id:
                continue
            record = _find_asset(asset_type, asset_id)
            if record is None or record.get("system"):
                manifest["system_refs"].append({"slot": key, "type": asset_type, "id": asset_id})
                continue
            path = _safe_asset_path(record["path"])
            if path.is_file():
                arcname = f"files/{record['path']}"
                archive.write(path, arcname)
                manifest["files"].append({"slot": key, "type": asset_type, "id": asset_id, "path": record["path"], "name": record["name"], "media": record.get("media")})
            elif path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file():
                        relative = child.relative_to(ASSETS_DIR).as_posix()
                        archive.write(child, f"files/{relative}")
                manifest["files"].append({"slot": key, "type": asset_type, "id": asset_id, "path": record["path"], "name": record["name"], "media": "pack"})
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return buffer.getvalue(), f"{preset['id']}.wvpack"


def import_pack(payload: bytes) -> dict:
    if not payload:
        raise ValueError("没有读到主题包")
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("主题包不是有效的 zip") from exc
    try:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8-sig"))
    except KeyError as exc:
        raise ValueError("主题包缺少 manifest.json") from exc
    if not isinstance(manifest, dict):
        raise ValueError("manifest.json 格式不对")
    if manifest.get("format") == "weaveverse-preset" and manifest.get("spec") == 2:
        return _import_preset_pack(archive, manifest)
    return _import_legacy_pack(archive, manifest)


def _import_preset_pack(archive: zipfile.ZipFile, manifest: dict) -> dict:
    warnings = []
    id_map = {}
    for item in manifest.get("files") or []:
        if not isinstance(item, dict):
            continue
        new_id = _copy_pack_files(archive, item)
        id_map[(item.get("type"), item.get("id"))] = new_id
    preset = _clean_preset(manifest.get("preset") or {})
    for key, asset_type in (("colors", "colors"), ("background", "backgrounds"), ("splash", "splashes"), ("icons", "icons")):
        old = preset["slots"].get(key)
        mapped = id_map.get((asset_type, old))
        if mapped:
            preset["slots"][key] = mapped
        elif old and _find_asset(asset_type, old) is None and old not in BUILTIN:
            warnings.append(key)
            preset["slots"][key] = "warm" if key == "colors" else None
    preset["id"] = f"p-{uuid.uuid4().hex[:8]}"
    preset["system"] = False
    preset["author"] = preset["author"] or "导入"
    saved = _save_preset(preset)
    return {"preset": saved, "warnings": warnings}


def _copy_pack_files(archive: zipfile.ZipFile, item: dict) -> str:
    asset_type = item.get("type")
    if asset_type not in ASSET_TYPES:
        raise ValueError("主题包里有不认识的素材")
    asset_id = f"u-{uuid.uuid4().hex[:10]}"
    prefix = f"files/{item.get('path')}"
    names = [name for name in archive.namelist() if name.startswith(prefix)]
    if item.get("media") == "pack" or str(item.get("path") or "").startswith("icons/"):
        folder = _safe_asset_path(f"icons/{asset_id}")
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            if name.endswith("/"):
                continue
            target = folder / Path(name).name
            target.write_bytes(archive.read(name))
        _add_asset("icons", {"id": asset_id, "name": item.get("name") or asset_id, "system": False, "path": f"icons/{asset_id}", "media": "pack"})
        return asset_id
    if not names:
        raise ValueError("主题包缺少素材文件")
    suffix = Path(names[0]).suffix.lower()
    relative = f"user/{asset_id}{suffix}"
    _safe_asset_path(relative).parent.mkdir(parents=True, exist_ok=True)
    _safe_asset_path(relative).write_bytes(archive.read(names[0]))
    _add_asset(asset_type, {
        "id": asset_id,
        "name": str(item.get("name") or asset_id)[:40],
        "system": False,
        "path": relative,
        "media": item.get("media") or _media_kind(asset_type, suffix),
    })
    return asset_id


def _import_legacy_pack(archive: zipfile.ZipFile, manifest: dict) -> dict:
    """Turn an M10.1 pack into a color asset plus a user preset.

    startup.mp4 is left out. That file is a boot recording with another product's
    interface, and it is not used as splash or wallpaper.
    """
    colors_name = str(manifest.get("colors") or "colors.json")
    try:
        theme = parse_theme_bytes(archive.read(colors_name))
    except KeyError as exc:
        raise ValueError("旧主题包缺少颜色文件") from exc
    theme["id"] = f"c-{uuid.uuid4().hex[:8]}"
    color = _store_color(theme, system=False, name=str(manifest.get("name") or theme["name"]))
    slots = {"colors": color["id"], "background": None, "splash": None, "icons": None}
    skipped = []
    for slot, spec in (("splash", manifest.get("splash")), ("background", manifest.get("background"))):
        if not isinstance(spec, dict):
            continue
        relative = str(spec.get("path") or "")
        if not relative or Path(relative).name.lower() in SKIP_MEDIA_NAMES:
            skipped.append(slot)
            continue
        try:
            payload = archive.read(relative)
        except KeyError:
            skipped.append(slot)
            continue
        asset_type = "splashes" if slot == "splash" else "backgrounds"
        stored = store_upload(asset_type, Path(relative).name, payload, Path(relative).stem)
        slots[slot] = stored["id"]
    preset = create_preset(str(manifest.get("name") or "导入的预设"), slots, None, None, inherit_base=False)
    return {"preset": preset, "warnings": skipped, "skipped_startup_video": "splash" in skipped or "background" in skipped}


def import_theme_file(payload: bytes) -> dict:
    theme = parse_theme_bytes(payload)
    if theme["id"] in BUILTIN:
        theme["id"] = f"c-{uuid.uuid4().hex[:8]}"
    return _store_color(theme, system=False)


def ensure_library() -> None:
    global _ready, _ensuring
    if _ready or _ensuring:
        return
    _ensuring = True
    try:
        _ensure_system_colors()
        _ensure_phase3_presets()
        _migrate_appearance_once()
        legacy_pack_colors()
        _keep_dragon_colors_only()
        _ready = True
    finally:
        _ensuring = False


def _ensure_system_colors() -> None:
    for theme_id, item in BUILTIN.items():
        if _find_asset("colors", theme_id) and get_preset(theme_id):
            continue
        color = _store_color({
            "id": theme_id,
            "name": item["name"],
            "author": item["author"],
            "version": item["version"],
            "vars": item["vars"],
        }, system=True)
        if get_preset(theme_id) is None:
            _save_preset({
                "id": theme_id,
                "name": item["name"],
                "author": "Weaveverse",
                "system": True,
                "based_on": None,
                "slots": {"colors": color["id"], "background": None, "splash": None, "icons": None},
                "slot_config": {"splash": {"duration": 2, "slogan": ""}},
            })


def _empty_preset(preset_id: str, name: str, color_id: str, system: bool) -> dict:
    return {
        "id": preset_id,
        "name": name,
        "author": "Weaveverse" if system else "用户",
        "system": system,
        "based_on": None,
        "slots": {"colors": color_id, "background": None, "splash": None, "icons": None},
        "slot_config": {"splash": {"duration": 2, "slogan": ""}},
    }


def _put_color(theme_id: str, name: str, vars_: dict, system: bool) -> None:
    if _find_asset("colors", theme_id):
        return
    _store_color({
        "id": theme_id,
        "name": name,
        "author": "Weaveverse",
        "version": "1.0.0",
        "vars": vars_,
    }, system=system, name=name)


def _put_preset(preset: dict) -> None:
    if get_preset(preset["id"]) is None:
        _save_preset(preset)


def _ensure_phase3_presets() -> None:
    """Mist purple is a system palette. The two game shells are user presets with empty media slots."""
    mist = {
        "dawn": "#efe6f3",
        "group": "#e2d6ea",
        "nav": "rgba(243, 236, 247, 0.92)",
        "work": "rgba(249, 246, 251, 0.94)",
        "orb": "#6a5b96",
        "progress": "#9a8bc4",
    }
    _put_color("mist-purple", "雾紫", mist, True)
    _put_preset(_empty_preset("mist-purple", "雾紫", "mist-purple", True))
    for preset_id in ("warm", "sakura", "mist-purple"):
        current = get_preset(preset_id)
        if current and current["system"] and (current["slots"]["background"] or current["slots"]["splash"] or current["slots"]["icons"]):
            current["slots"]["background"] = None
            current["slots"]["splash"] = None
            current["slots"]["icons"] = None
            _save_preset(current)
    yihuan = {
        "dawn": "#e4edf4",
        "group": "#d0dee9",
        "nav": "rgba(233, 241, 247, 0.92)",
        "work": "rgba(245, 248, 251, 0.94)",
        "orb": "#3a679f",
        "progress": "#6a8fbe",
    }
    seer = {
        "dawn": "#e6f3df",
        "group": "#d2e6c8",
        "nav": "rgba(236, 245, 232, 0.92)",
        "work": "rgba(246, 250, 242, 0.94)",
        "orb": "#2e8644",
        "progress": "#62a86a",
    }
    _put_color("yihuan-colors", "异环冷钢", yihuan, False)
    _put_color("seer-colors", "赛尔叶绿", seer, False)
    _put_preset(_empty_preset("yihuan-personal", "异环（我的）", "yihuan-colors", False))
    _put_preset(_empty_preset("seer-peak-personal", "赛尔号巅峰之战（我的）", "seer-colors", False))


def _keep_dragon_colors_only() -> None:
    preset = get_preset("dragon-girl")
    if preset is None:
        return
    slots = dict(preset["slots"])
    changed = False
    for key, asset_type in (("background", "backgrounds"), ("splash", "splashes"), ("icons", "icons")):
        asset_id = slots.get(key)
        if not asset_id:
            continue
        record = _find_asset(asset_type, asset_id)
        name = Path(record["path"]).name.lower() if record else ""
        if name in SKIP_MEDIA_NAMES:
            slots[key] = None
            changed = True
    if changed:
        preset["slots"] = slots
        _save_preset(preset)


def _migrate_appearance_once() -> None:
    from app.appearance import SETTINGS_PATH, load_settings

    raw = {}
    if SETTINGS_PATH.exists():
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
    if isinstance(raw, dict) and raw.get("library_ready"):
        return
    current = load_settings()
    for theme in current.get("custom_themes") or []:
        if isinstance(theme, dict) and theme.get("id") and theme["id"] not in BUILTIN and _find_asset("colors", theme["id"]) is None:
            _store_color(theme, system=False)
    slots = {"colors": current.get("theme") if current.get("theme") in BUILTIN or _find_asset("colors", current.get("theme") or "") else "warm", "background": None, "splash": None, "icons": None}
    background_id = _adopt_legacy_file(BACKGROUNDS_DIR / (current.get("global_video") or ""), "backgrounds", current.get("global_video_name") or "")
    if background_id is None:
        background_id = _adopt_legacy_file(BACKGROUNDS_DIR / (current.get("global_image") or ""), "backgrounds", current.get("global_image_name") or "")
    slots["background"] = background_id
    if current.get("splash_owner") == "user":
        slots["splash"] = _adopt_legacy_file(SPLASH_DIR / (current.get("splash_file") or ""), "splashes", current.get("splash_name") or "")
    current["slots"] = slots
    matched = None
    for preset in list_presets():
        if preset["system"] and preset["slots"] == slots and not background_id and not slots["splash"]:
            matched = preset["id"]
            break
    if matched is None and slots["colors"] in BUILTIN and not background_id and not slots["splash"]:
        matched = slots["colors"]
    current["current_preset"] = matched or ""
    current["dirty"] = False
    current["library_ready"] = True
    _write_appearance(current)


def _adopt_legacy_file(path: Path, asset_type: str, name: str) -> str | None:
    if not path.is_file() or path.name.lower() in SKIP_MEDIA_NAMES:
        return None
    asset_id = f"u-{uuid.uuid4().hex[:10]}"
    suffix = path.suffix.lower()
    try:
        kind = _media_kind(asset_type, suffix)
    except ValueError:
        return None
    relative = f"user/{asset_id}{suffix}"
    target = _safe_asset_path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    _add_asset(asset_type, {
        "id": asset_id,
        "name": (name or path.stem)[:40],
        "system": False,
        "path": relative,
        "media": kind,
    })
    return asset_id


def legacy_pack_colors() -> None:
    """Register colors from an installed M10.1 pack without copying startup.mp4."""
    folder = THEMES_DIR / "dragon-girl"
    manifest_path = folder / "manifest.json"
    if not manifest_path.is_file() or get_preset("dragon-girl"):
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        theme = parse_theme_bytes((folder / str(manifest.get("colors") or "colors.json")).read_bytes())
    except (OSError, json.JSONDecodeError, ValueError):
        return
    theme["id"] = "dragon-girl"
    color = _store_color(theme, system=False, name=str(manifest.get("name") or "龙娘主题"))
    _save_preset({
        "id": "dragon-girl",
        "name": str(manifest.get("name") or "龙娘主题"),
        "author": "用户",
        "system": False,
        "based_on": None,
        "slots": {"colors": color["id"], "background": None, "splash": None, "icons": None},
        "slot_config": {"splash": {"duration": 2, "slogan": ""}},
    })
