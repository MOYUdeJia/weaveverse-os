"""Create encrypted backups in data/backups and restore them."""

from __future__ import annotations

from fastapi import APIRouter, Form, UploadFile
from pydantic import BaseModel, Field

from app.backup_file import (
    backup_path,
    decrypt_backup,
    delete_backup,
    last_backup_at,
    list_backups,
    restore_zip,
    write_backup,
)
from app.errors import raise_api_error
from sqlmodel import Session

from app.db import engine
from app.privacy import require_session, status as privacy_status
from app import vault_crud

router = APIRouter(prefix="/backup", tags=["backup"])


class BackupNow(BaseModel):
    label: str = Field(default="", max_length=40)


class BackupRestoreNamed(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    password: str = Field(default="", max_length=200)


class BackupDelete(BaseModel):
    filename: str = Field(min_length=1, max_length=200)


@router.get("")
def backup_info() -> dict:
    return {
        "last_backup_at": last_backup_at(),
        "items": list_backups(),
        "security_set": privacy_status()["security_set"],
        "backup_set": privacy_status()["backup_set"],
        "backup_unlocked": privacy_status()["backup_unlocked"],
    }


@router.post("/export")
def export_backup(data: BackupNow) -> dict:
    try:
        password = require_session("backup")
    except PermissionError as exc:
        field = "password"
        message = str(exc)
        if "设置" in message:
            field = "backup"
        raise_api_error(409, field, message)
    try:
        with Session(engine) as session:
            plain = vault_crud.export_plaintext(session, password)
        result = write_backup(password, data.label, plain)
    except ValueError as exc:
        raise_api_error(400, "backup", str(exc))
    except Exception:
        raise_api_error(500, "backup", "备份没有做成")
    return result


def _restore(blob: bytes, file_password: str) -> dict:
    try:
        current = require_session("backup")
    except PermissionError as exc:
        raise_api_error(409, "password", str(exc))
    opener = file_password.strip() or current
    try:
        payload = decrypt_backup(blob, opener)
        restore_zip(payload, current, opener)
    except ValueError as exc:
        raise_api_error(400, "password", str(exc))
    except Exception:
        raise_api_error(500, "backup", "恢复没有完成")
    return {"ok": True, "restart": True}


@router.post("/restore")
async def import_backup(file: UploadFile, password: str = Form(default="")) -> dict:
    blob = await file.read()
    try:
        return _restore(blob, password)
    finally:
        password = ""


@router.post("/restore-named")
def restore_named(data: BackupRestoreNamed) -> dict:
    try:
        path = backup_path(data.filename)
    except ValueError as exc:
        raise_api_error(400, "filename", str(exc))
    if not path.is_file():
        raise_api_error(404, "filename", "找不到这个备份")
    try:
        return _restore(path.read_bytes(), data.password)
    finally:
        data.password = ""


@router.post("/delete")
def remove_backup(data: BackupDelete) -> dict:
    try:
        delete_backup(data.filename)
    except ValueError as exc:
        raise_api_error(400, "filename", str(exc))
    except FileNotFoundError as exc:
        raise_api_error(404, "filename", str(exc))
    return {"ok": True, "items": list_backups()}
