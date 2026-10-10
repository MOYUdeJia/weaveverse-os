"""HTTP routes for theme, bar style, and background files."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse

from app.appearance import (
    assign_file,
    background_path,
    clear_file,
    load_settings,
    save_settings,
    store_image,
    store_video,
)
from app.errors import raise_api_error


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
        if kind == "video":
            if suffix != ".mp4":
                raise ValueError("视频只支持 mp4")
            filename = store_video(payload)
        else:
            filename = store_image(payload, suffix or ".png")
        return assign_file("video" if kind == "video" else "image", filename, group_id)
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
