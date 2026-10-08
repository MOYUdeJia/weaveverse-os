"""HTTP routes for cropped navigation icons."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.db import get_session
from app.errors import raise_api_error
from app.icon_files import delete_icon_id, icon_file_id, icon_path, save_icon_png


router = APIRouter(prefix="/icons", tags=["icons"])


@router.post("")
# 保存前端裁好的 PNG，返回 @file: 引用。
# Store a PNG already cropped in the browser and return its @file: reference.
async def upload_icon(file: UploadFile, session: Session = Depends(get_session)) -> dict[str, str]:
    del session
    payload = await file.read()
    if not payload:
        raise_api_error(400, "file", "空文件")
    try:
        icon = save_icon_png(payload)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))
    return {"icon": icon}


@router.get("/{filename}")
# 读取一张导航图标。
# Serve one navigation icon.
def get_icon(filename: str):
    icon_id = filename[:-4] if filename.endswith(".png") else ""
    if icon_file_id(f"@file:{icon_id}") is None:
        raise_api_error(404, "filename", "图标不存在")
    path = icon_path(icon_id)
    if not path.is_file():
        raise_api_error(404, "filename", "图标不存在")
    return FileResponse(path, media_type="image/png")


@router.delete("/{filename}")
# 删除还没被导航引用的图标。
# Delete an icon that no navigation item references.
def remove_icon(filename: str, session: Session = Depends(get_session)) -> dict[str, str]:
    icon_id = filename[:-4] if filename.endswith(".png") else ""
    if icon_file_id(f"@file:{icon_id}") is None:
        raise_api_error(400, "filename", "图标引用无效")
    path = icon_path(icon_id)
    delete_icon_id(session, icon_id)
    if path.is_file():
        raise_api_error(409, "filename", "图标仍在使用")
    return {"status": "ok"}
