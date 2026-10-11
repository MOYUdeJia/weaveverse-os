"""Export and restore an encrypted .wvbak archive. The password is not stored."""

from __future__ import annotations

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.backup_file import decrypt_backup, encrypt_backup, last_backup_at, remember_backup, restore_zip
from app.errors import raise_api_error

router = APIRouter(prefix="/backup", tags=["backup"])


class BackupCreate(BaseModel):
    password: str = Field(min_length=8, max_length=200)


@router.get("")
def backup_info() -> dict:
    return {"last_backup_at": last_backup_at()}


@router.post("/export")
def export_backup(data: BackupCreate) -> Response:
    try:
        blob = encrypt_backup(data.password)
    except Exception:
        raise_api_error(500, "backup", "备份没有做成")
    finally:
        data.password = ""
    remember_backup()
    return Response(
        blob,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=weaveverse.wvbak"},
    )


@router.post("/restore")
async def import_backup(file: UploadFile, password: str = Form()) -> dict:
    if len(password) < 8:
        raise_api_error(400, "password", "密码至少 8 位")
    blob = await file.read()
    try:
        payload = decrypt_backup(blob, password)
        restore_zip(payload)
    except ValueError as exc:
        raise_api_error(400, "password", str(exc))
    except Exception:
        raise_api_error(500, "backup", "恢复没有完成")
    finally:
        password = ""
    return {"ok": True, "restart": True}
