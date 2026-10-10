"""HTTP routes for photo albums and the photo metadata layer."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, UploadFile
from sqlmodel import Session

from app import photo_crud
from app.album_lock import check_album_password
from app.config import ATTACHMENTS_DIR
from app.db import get_session
from app.errors import raise_api_error
from app.routes.blocks import ALLOWED_IMAGE_SUFFIXES, MAX_FILE_BYTES, _safe_attachment_path
from app.schemas import (
    AlbumCreate,
    AlbumRead,
    AlbumUnlock,
    AlbumUpdate,
    PhotoBulkDelete,
    PhotoLink,
    PhotoMove,
    PhotoRead,
    PhotoRename,
)

router = APIRouter(prefix="/photos", tags=["photos"])


def _ensure_attachment(filename: str) -> str:
    path = _safe_attachment_path(filename)
    if not path.is_file():
        raise_api_error(404, "filename", "附件不存在")
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise_api_error(400, "filename", "仅支持 png / jpg / jpeg / gif / webp")
    return filename


def _password(album_password: str | None) -> str | None:
    return album_password


@router.get("/albums", response_model=list[AlbumRead])
def list_albums(session: Session = Depends(get_session)) -> list[dict]:
    return [photo_crud.album_to_dict(row) for row in photo_crud.list_albums(session)]


@router.post("/albums", response_model=AlbumRead)
def create_album(data: AlbumCreate, session: Session = Depends(get_session)) -> dict:
    if data.is_private and len(data.password.strip()) < 4:
        raise_api_error(400, "password", "隐私相册密码至少 4 位")
    row = photo_crud.create_album(session, data.name, data.is_private, data.password.strip())
    return photo_crud.album_to_dict(row)


@router.patch("/albums/{album_id}", response_model=AlbumRead)
def update_album(album_id: int, data: AlbumUpdate, session: Session = Depends(get_session)) -> dict:
    row = photo_crud.get_album(session, album_id)
    if row is None:
        raise_api_error(404, "id", "相册不存在")
    if data.is_private is True and (data.password is None or len(data.password.strip()) < 4):
        raise_api_error(400, "password", "隐私相册密码至少 4 位")
    try:
        updated = photo_crud.update_album(
            session,
            row,
            name=data.name,
            is_private=data.is_private,
            password=None if data.password is None else data.password.strip(),
        )
    except ValueError as exc:
        raise_api_error(400, "password", str(exc))
    return photo_crud.album_to_dict(updated)


@router.post("/albums/{album_id}/unlock")
def unlock_album(album_id: int, data: AlbumUnlock, session: Session = Depends(get_session)) -> dict[str, bool]:
    row = photo_crud.get_album(session, album_id)
    if row is None:
        raise_api_error(404, "id", "相册不存在")
    if not row.is_private:
        return {"ok": True}
    if not check_album_password(album_id, data.password):
        raise_api_error(401, "password", "密码不对")
    return {"ok": True}


@router.delete("/albums/{album_id}")
def delete_album(album_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    row = photo_crud.get_album(session, album_id)
    if row is None:
        raise_api_error(404, "id", "相册不存在")
    photo_crud.delete_album(session, row)
    return {"status": "ok"}


@router.get("", response_model=list[PhotoRead])
def list_photos(
    album_id: int | None = None,
    album_password: str | None = Header(default=None, alias="Album-Password"),
    session: Session = Depends(get_session),
) -> list[dict]:
    try:
        rows = photo_crud.list_photos(session, album_id, _password(album_password))
    except PermissionError as exc:
        raise_api_error(401, "password", str(exc))
    except LookupError as exc:
        raise_api_error(404, "album_id", str(exc))
    return [photo_crud.photo_to_dict(row) for row in rows]


@router.post("", response_model=PhotoRead)
def link_photo(
    data: PhotoLink,
    album_password: str | None = Header(default=None, alias="Album-Password"),
    session: Session = Depends(get_session),
) -> dict:
    filename = _ensure_attachment(data.filename)
    try:
        row = photo_crud.add_photo(session, filename, data.note, data.album_id, _password(album_password))
    except PermissionError as exc:
        raise_api_error(401, "password", str(exc))
    except LookupError as exc:
        raise_api_error(404, "album_id", str(exc))
    return photo_crud.photo_to_dict(row)


@router.post("/upload", response_model=PhotoRead)
async def upload_photo(
    file: UploadFile,
    album_id: int | None = None,
    album_password: str | None = Header(default=None, alias="Album-Password"),
    session: Session = Depends(get_session),
) -> dict:
    original_name = file.filename or "image.png"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise_api_error(400, "file", "仅支持 png / jpg / jpeg / gif / webp")

    payload = await file.read()
    if not payload:
        raise_api_error(400, "file", "空文件")
    if len(payload) > MAX_FILE_BYTES:
        raise_api_error(400, "file", "文件超过 20MB")

    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = ATTACHMENTS_DIR / filename
    target.write_bytes(payload)
    note = Path(original_name).stem
    try:
        row = photo_crud.add_photo(session, filename, note, album_id, _password(album_password))
    except PermissionError as exc:
        target.unlink(missing_ok=True)
        raise_api_error(401, "password", str(exc))
    except LookupError as exc:
        target.unlink(missing_ok=True)
        raise_api_error(404, "album_id", str(exc))
    return photo_crud.photo_to_dict(row)


@router.patch("/{photo_id}", response_model=PhotoRead)
def rename_photo(photo_id: int, data: PhotoRename, session: Session = Depends(get_session)) -> dict:
    row = photo_crud.get_photo(session, photo_id)
    if row is None:
        raise_api_error(404, "id", "图片不在库里")
    updated = photo_crud.rename_photo(session, row, data.display_name)
    return photo_crud.photo_to_dict(updated)


@router.post("/move")
def move_photos(
    data: PhotoMove,
    album_password: str | None = Header(default=None, alias="Album-Password"),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    try:
        count = photo_crud.move_photos(session, data.ids, data.album_id, _password(album_password))
    except PermissionError as exc:
        raise_api_error(401, "password", str(exc))
    except LookupError as exc:
        raise_api_error(404, "album_id", str(exc))
    return {"moved": count}


@router.post("/bulk-delete")
def bulk_delete_photos(data: PhotoBulkDelete, session: Session = Depends(get_session)) -> dict[str, int]:
    return {"deleted": photo_crud.delete_photos(session, data.ids)}


@router.delete("/{photo_id}")
def delete_photo(photo_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    row = photo_crud.get_photo(session, photo_id)
    if row is None:
        raise_api_error(404, "id", "图片不在库里")
    photo_crud.delete_photo(session, row)
    return {"status": "ok"}
