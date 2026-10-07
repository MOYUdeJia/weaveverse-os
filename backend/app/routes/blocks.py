"""HTTP routes for updating, deleting, and attaching files to blocks."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from app import crud
from app.config import ATTACHMENTS_DIR
from app.db import get_session
from app.errors import raise_api_error
from app.schemas import BlockUpdate


router = APIRouter(tags=["blocks"])

ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


# 把附件文件名限制在 attachments 目录内。
# Keep attachment filenames inside the attachments directory.
def _safe_attachment_path(filename: str) -> Path:
    name = Path(filename).name
    if name != filename or name in {"", ".", ".."} or "/" in filename or "\\" in filename:
        raise_api_error(400, "filename", "非法文件名")
    return ATTACHMENTS_DIR / name


@router.put("/blocks/{block_id}")
# 更新区块内容。
# Update a block's content.
def update_block(block_id: int, data: BlockUpdate, session: Session = Depends(get_session)):
    block = crud.get_block(session, block_id)
    if block is None:
        raise_api_error(404, "id", "区块不存在")
    try:
        updated = crud.update_block(session, block, data)
    except ValueError as exc:
        raise_api_error(400, "content", str(exc))
    return crud.block_to_dict(updated)


@router.delete("/blocks/{block_id}")
# 删除一个区块。
# Delete one block.
def delete_block(block_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    block = crud.get_block(session, block_id)
    if block is None:
        raise_api_error(404, "id", "区块不存在")
    crud.delete_block(session, block)
    return {"status": "ok"}


@router.post("/blocks/{block_id}/images")
# 把图片存到 attachments 目录，不改区块 content。
# Store an image in attachments without changing block content.
async def upload_block_image(block_id: int, file: UploadFile, session: Session = Depends(get_session)):
    block = crud.get_block(session, block_id)
    if block is None:
        raise_api_error(404, "id", "区块不存在")

    original_name = file.filename or "image.png"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise_api_error(400, "file", "仅支持 png / jpg / jpeg / gif / webp")

    payload = await file.read()
    if not payload:
        raise_api_error(400, "file", "空文件")

    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = ATTACHMENTS_DIR / filename
    target.write_bytes(payload)
    return {"filename": filename}


@router.get("/attachments/{filename}")
# 读取一张本地附件。
# Serve one local attachment file.
def get_attachment(filename: str):
    path = _safe_attachment_path(filename)
    if not path.is_file():
        raise_api_error(404, "filename", "附件不存在")
    return FileResponse(path)


@router.delete("/attachments/{filename}")
# 删除一张本地附件。
# Delete one local attachment file.
def delete_attachment(filename: str) -> dict[str, str]:
    path = _safe_attachment_path(filename)
    if not path.is_file():
        raise_api_error(404, "filename", "附件不存在")
    path.unlink()
    return {"status": "ok"}
