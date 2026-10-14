"""Builtin palettes and .wvtheme import / export helpers."""

from __future__ import annotations

import json
import re
import uuid

THEME_FORMAT = "weaveverse-theme"
THEME_SPEC = 1
MAX_THEME_BYTES = 64 * 1024
MAX_CUSTOM = 24
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
COLOR_PATTERN = re.compile(
    r"^(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{8}|rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\))$"
)
VAR_KEYS = ("dawn", "group", "nav", "work", "orb", "progress")

BUILTIN = {
    "warm": {
        "name": "暖白",
        "author": "Weaveverse",
        "version": "1.0.0",
        "vars": {
            "dawn": "#f4efe7",
            "group": "#efeae1",
            "nav": "rgba(248, 245, 238, 0.92)",
            "work": "rgba(252, 250, 245, 0.94)",
            "orb": "#f4efe7",
            "progress": "#3f6f57",
        },
    },
    "mint": {
        "name": "薄荷",
        "author": "Weaveverse",
        "version": "1.0.0",
        "vars": {
            "dawn": "#e5f4ee",
            "group": "#d7eee4",
            "nav": "rgba(236, 248, 242, 0.92)",
            "work": "rgba(244, 252, 248, 0.94)",
            "orb": "#e5f4ee",
            "progress": "#3f6f57",
        },
    },
    "sky": {
        "name": "天蓝",
        "author": "Weaveverse",
        "version": "1.0.0",
        "vars": {
            "dawn": "#e7f1fb",
            "group": "#d5e6f6",
            "nav": "rgba(238, 246, 252, 0.92)",
            "work": "rgba(246, 250, 253, 0.94)",
            "orb": "#e7f1fb",
            "progress": "#3f6f57",
        },
    },
    "sakura": {
        "name": "樱粉",
        "author": "Weaveverse",
        "version": "1.0.0",
        "vars": {
            "dawn": "#fbeaf0",
            "group": "#f6dbe6",
            "nav": "rgba(253, 242, 246, 0.92)",
            "work": "rgba(255, 248, 250, 0.94)",
            "orb": "#fbeaf0",
            "progress": "#3f6f57",
        },
    },
    "ash": {
        "name": "灰调",
        "author": "Weaveverse",
        "version": "1.0.0",
        "vars": {
            "dawn": "#eceeef",
            "group": "#e1e4e6",
            "nav": "rgba(244, 245, 246, 0.92)",
            "work": "rgba(248, 249, 249, 0.94)",
            "orb": "#eceeef",
            "progress": "#3f6f57",
        },
    },
}


def builtin_ids() -> set[str]:
    return set(BUILTIN)


def _clean_color(value: object) -> str:
    text = str(value or "").strip()
    if not COLOR_PATTERN.fullmatch(text):
        raise ValueError("颜色只支持 #RRGGBB / #RRGGBBAA / rgb() / rgba()")
    return text


def _clean_vars(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("主题缺少 vars")
    vars_: dict[str, str] = {}
    for key in VAR_KEYS:
        if key not in raw:
            continue
        vars_[key] = _clean_color(raw[key])
    for required in ("dawn", "group", "nav", "work"):
        if required not in vars_:
            raise ValueError(f"主题缺少 {required} 颜色")
    return vars_


def _clean_id(value: object, fallback: str = "") -> str:
    text = re.sub(r"[^a-z0-9-]", "-", str(value or "").strip().lower())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if not ID_PATTERN.fullmatch(text):
        text = fallback or f"c-{uuid.uuid4().hex[:10]}"
    if text in BUILTIN:
        text = f"c-{text}"
    return text[:40]


def parse_theme_bytes(payload: bytes) -> dict:
    if not payload:
        raise ValueError("没有读到主题文件")
    if len(payload) > MAX_THEME_BYTES:
        raise ValueError("主题文件超过 64KB")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("主题文件不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("主题文件格式不对")
    if data.get("format") not in {THEME_FORMAT, "wvtheme", None}:
        if "vars" not in data:
            raise ValueError("不是 Weaveverse 主题文件")
    spec = data.get("spec") or data.get("version")
    if spec not in {None, THEME_SPEC, "1", "1.0", "1.0.0"}:
        try:
            if int(spec) != THEME_SPEC:
                raise ValueError("不支持的主题版本")
        except (TypeError, ValueError):
            if str(spec) not in {"1", "1.0", "1.0.0"}:
                raise ValueError("不支持的主题版本") from None
    theme_id = _clean_id(data.get("id") or data.get("name"))
    name = str(data.get("name") or theme_id)[:40]
    author = str(data.get("author") or "")[:40]
    version = str(data.get("version") or "1.0.0")[:16]
    return {
        "id": theme_id,
        "name": name,
        "author": author,
        "version": version,
        "vars": _clean_vars(data.get("vars")),
    }


def export_payload(theme_id: str, name: str, author: str, version: str, vars_: dict) -> dict:
    return {
        "format": THEME_FORMAT,
        "spec": THEME_SPEC,
        "id": theme_id,
        "name": name,
        "author": author,
        "version": version,
        "vars": vars_,
    }


def builtin_export(theme_id: str) -> dict:
    if theme_id not in BUILTIN:
        raise ValueError("没有这个预设主题")
    item = BUILTIN[theme_id]
    return export_payload(theme_id, item["name"], item["author"], item["version"], item["vars"])


def upsert_custom(existing: list, incoming: dict) -> list[dict]:
    cleaned = []
    replaced = False
    for item in existing:
        if not isinstance(item, dict):
            continue
        if item.get("id") == incoming["id"]:
            cleaned.append(incoming)
            replaced = True
        else:
            cleaned.append(item)
    if not replaced:
        if len(cleaned) >= MAX_CUSTOM:
            raise ValueError("自定义主题最多 24 套")
        cleaned.append(incoming)
    return cleaned


def drop_custom(existing: list, theme_id: str) -> list[dict]:
    return [item for item in existing if isinstance(item, dict) and item.get("id") != theme_id]


def find_custom(existing: list, theme_id: str) -> dict | None:
    for item in existing:
        if isinstance(item, dict) and item.get("id") == theme_id:
            return item
    return None
