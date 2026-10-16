"""HTTP routes for theme, bar style, splash covers, and background files."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse, Response

from app.appearance import (
    activate_pack,
    assign_file,
    assign_splash,
    background_path,
    clear_file,
    clear_splash,
    delete_pack,
    import_theme,
    load_settings,
    remove_theme,
    save_settings,
    store_image,
    store_video,
)
from app.packs import install_pack, pack_file
from app.errors import raise_api_error
from app.splash import splash_path, store_splash
from app.themes import BUILTIN, builtin_export, export_payload, find_custom, parse_theme_bytes


router = APIRouter(prefix="/appearance", tags=["appearance"])


@router.get("")
def get_appearance() -> dict:
    return load_settings()


@router.put("")
def put_appearance(data: dict) -> dict:
    return save_settings(data if isinstance(data, dict) else {})


@router.post("/files")
async def upload_background(file: UploadFile, kind: str = "image", group_id: int | None = None) -> dict:
    payload = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    try:
        label = Path(file.filename or "").name
        if kind == "video":
            if suffix != ".mp4":
                raise ValueError("视频只支持 mp4")
            filename = store_video(payload)
        else:
            filename = store_image(payload, suffix or ".png")
        return assign_file("video" if kind == "video" else "image", filename, group_id, label)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))


@router.delete("/files")
def delete_background(kind: str = "image", group_id: int | None = None) -> dict:
    return clear_file(kind, group_id)


@router.get("/files/{filename}")
def read_background(filename: str):
    try:
        path = background_path(filename)
    except ValueError as exc:
        raise_api_error(400, "filename", str(exc))
    if not path.is_file():
        raise_api_error(404, "filename", "背景不存在")
    return FileResponse(path)


@router.post("/splash")
async def upload_splash(file: UploadFile) -> dict:
    payload = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    try:
        filename, kind = store_splash(payload, suffix)
        return assign_splash(filename, kind, Path(file.filename or "").name)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))


@router.delete("/splash")
def delete_splash() -> dict:
    return clear_splash()


@router.get("/splash/{filename}")
def read_splash(filename: str):
    try:
        path = splash_path(filename)
    except ValueError as exc:
        raise_api_error(400, "filename", str(exc))
    if not path.is_file():
        raise_api_error(404, "filename", "封面不存在")
    return FileResponse(path)


@router.post("/themes")
async def upload_theme(file: UploadFile) -> dict:
    payload = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    try:
        if suffix == ".wvpack":
            install_pack(payload)
            return load_settings()
        theme = parse_theme_bytes(payload)
        return import_theme(theme)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))


@router.post("/packs/{pack_id}/activate")
def use_pack(pack_id: str) -> dict:
    try:
        return activate_pack(pack_id)
    except ValueError as exc:
        raise_api_error(400, "pack", str(exc))


@router.delete("/packs/{pack_id}")
def drop_pack(pack_id: str) -> dict:
    try:
        return delete_pack(pack_id)
    except ValueError as exc:
        raise_api_error(400, "pack", str(exc))


@router.get("/packs/{pack_id}/files/{file_path:path}")
def read_pack_file(pack_id: str, file_path: str):
    try:
        path = pack_file(pack_id, file_path)
    except ValueError as exc:
        raise_api_error(404, "file", str(exc))
    return FileResponse(path)


@router.delete("/themes/{theme_id}")
def delete_theme(theme_id: str) -> dict:
    try:
        return remove_theme(theme_id)
    except ValueError as exc:
        raise_api_error(400, "theme", str(exc))


@router.get("/themes/export")
def export_theme():
    settings = load_settings()
    theme_id = settings.get("theme") or "warm"
    try:
        if theme_id in BUILTIN:
            payload = builtin_export(theme_id)
        else:
            custom = find_custom(settings.get("custom_themes") or [], theme_id)
            if custom is None:
                raise ValueError("没有可导出的主题")
            payload = export_payload(
                custom["id"],
                custom.get("name") or custom["id"],
                custom.get("author") or "",
                custom.get("version") or "1.0.0",
                custom.get("vars") or {},
            )
    except ValueError as exc:
        raise_api_error(400, "theme", str(exc))
    name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in payload["id"]) or "theme"
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}.wvtheme"'},
    )
