"""HTTP routes for the asset library, presets, and live slots."""

from __future__ import annotations

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.errors import raise_api_error
from app.library import (
    DirtyPreset,
    apply_preset,
    asset_file,
    icon_entry,
    list_icon_entries,
    create_preset,
    delete_asset,
    delete_preset,
    export_preset,
    get_preset,
    import_pack,
    import_theme_file,
    list_assets,
    list_presets,
    patch_slots,
    slot_state,
    store_upload,
    update_preset,
)


router = APIRouter(tags=["library"])


@router.get("/assets")
def get_assets(type: str | None = None) -> dict:
    try:
        return list_assets(type)
    except ValueError as exc:
        raise_api_error(400, "type", str(exc))


@router.post("/assets/upload")
async def post_assets(type: str = Form(...), files: list[UploadFile] = File(...)) -> dict:
    stored = []
    try:
        for item in files:
            stored.append(store_upload(type, item.filename or "", await item.read(), item.filename or ""))
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))
    return {"assets": stored}


@router.delete("/assets/{asset_type}/{asset_id}")
def remove_asset(asset_type: str, asset_id: str) -> dict:
    try:
        delete_asset(asset_type, asset_id)
    except ValueError as exc:
        raise_api_error(400, "asset", str(exc))
    return list_assets(asset_type)


@router.get("/assets/icons/{asset_id}/entries")
def get_icon_entries(asset_id: str) -> dict:
    try:
        return {"files": list_icon_entries(asset_id)}
    except ValueError as exc:
        raise_api_error(404, "asset", str(exc))


@router.get("/assets/icons/{asset_id}/entries/{filename}")
def read_icon_entry(asset_id: str, filename: str):
    try:
        return FileResponse(icon_entry(asset_id, filename))
    except ValueError as exc:
        raise_api_error(404, "file", str(exc))


@router.get("/assets/{asset_type}/{asset_id}/file")
def read_asset_file(asset_type: str, asset_id: str):
    try:
        path = asset_file(asset_type, asset_id)
    except ValueError as exc:
        raise_api_error(404, "asset", str(exc))
    if path.is_dir():
        raise_api_error(400, "asset", "图标包请读取里面的单张图")
    return FileResponse(path)


@router.get("/presets")
def get_presets() -> dict:
    return {"presets": list_presets()}


@router.post("/presets")
def post_preset(data: dict) -> dict:
    if not isinstance(data, dict):
        data = {}
    try:
        return create_preset(str(data.get("name") or ""), data.get("slots"), data.get("slot_config"), data.get("based_on"))
    except ValueError as exc:
        raise_api_error(400, "preset", str(exc))


@router.patch("/presets/{preset_id}")
def patch_preset(preset_id: str, data: dict) -> dict:
    try:
        return update_preset(preset_id, data if isinstance(data, dict) else {})
    except ValueError as exc:
        raise_api_error(400, "preset", str(exc))


@router.delete("/presets/{preset_id}")
def remove_preset(preset_id: str) -> dict:
    try:
        delete_preset(preset_id)
    except ValueError as exc:
        raise_api_error(400, "preset", str(exc))
    return {"presets": list_presets()}


@router.post("/presets/apply/{preset_id}")
def use_preset(preset_id: str, data: dict | None = Body(default=None)) -> dict:
    body = data if isinstance(data, dict) else {}
    try:
        return apply_preset(preset_id, str(body.get("resolution") or ""), str(body.get("name") or ""))
    except DirtyPreset as exc:
        raise HTTPException(status_code=409, detail={
            "field": "dirty",
            "message": "当前配置有未保存修改",
            "system": exc.system,
            "choices": ["save_as", "discard", "cancel"] if exc.system else ["save", "save_as", "discard", "cancel"],
        })
    except ValueError as exc:
        raise_api_error(400, "preset", str(exc))


@router.get("/slots")
def get_slots() -> dict:
    return slot_state()


@router.patch("/slots")
def update_slots(data: dict) -> dict:
    try:
        return patch_slots(data if isinstance(data, dict) else {})
    except ValueError as exc:
        raise_api_error(400, "slot", str(exc))


@router.post("/presets/export/{preset_id}")
def download_preset(preset_id: str):
    try:
        payload, filename = export_preset(preset_id)
    except ValueError as exc:
        raise_api_error(400, "preset", str(exc))
    return Response(content=payload, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/presets/import")
async def upload_preset(file: UploadFile) -> dict:
    name = (file.filename or "").lower()
    payload = await file.read()
    try:
        if name.endswith(".wvtheme") or (name.endswith(".json") and not name.endswith(".wvpack")):
            return {"asset": import_theme_file(payload)}
        return import_pack(payload)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))


@router.get("/presets/{preset_id}")
def read_preset(preset_id: str) -> dict:
    preset = get_preset(preset_id)
    if preset is None:
        raise_api_error(404, "preset", "预设不存在")
    return preset
