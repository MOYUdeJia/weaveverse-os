"""Set and unlock the vault master password and the backup password."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.errors import raise_api_error
from app import privacy, vault_crud

router = APIRouter(prefix="/privacy", tags=["privacy"])


class PasswordSet(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    current: str = Field(default="", max_length=200)


class PasswordUnlock(BaseModel):
    password: str = Field(min_length=1, max_length=200)


def _apply(kind: privacy.Kind, data: PasswordSet, session: Session | None = None) -> dict:
    secrets = []
    previous = privacy.snapshot_file()
    previous_session = privacy.session_password(kind)
    if kind == "vault" and privacy.status()["vault_set"]:
        if not data.current.strip():
            raise_api_error(401, "current", "请输入当前密码")
        try:
            privacy.unlock("vault", data.current)
            if session is not None:
                secrets = vault_crud.snapshot_secrets(session)
        except PermissionError as exc:
            raise_api_error(401, "current", str(exc))
        except Exception:
            raise_api_error(400, "password", "现有条目解不开，主密码没有改")
    try:
        privacy.set_password(kind, data.password, data.current)
        if kind == "vault" and secrets and session is not None:
            vault_crud.reencrypt_all(session, secrets)
    except PermissionError as exc:
        raise_api_error(401, "current", str(exc))
    except ValueError as exc:
        raise_api_error(400, "password", str(exc))
    except Exception:
        privacy.restore_file(previous)
        if previous_session:
            privacy.remember(kind, previous_session)
        else:
            privacy.lock(kind)
        raise_api_error(500, "password", "密码没有改完")
    finally:
        data.password = ""
        data.current = ""
    return privacy.status()


@router.get("")
def privacy_status() -> dict:
    return privacy.status()


@router.post("/vault")
def set_vault_password(data: PasswordSet, session: Session = Depends(get_session)) -> dict:
    return _apply("vault", data, session)


@router.post("/vault/unlock")
def unlock_vault(data: PasswordUnlock) -> dict:
    try:
        privacy.unlock("vault", data.password)
    except PermissionError as exc:
        raise_api_error(401, "password", str(exc))
    finally:
        data.password = ""
    return privacy.status()


@router.post("/vault/lock")
def lock_vault() -> dict:
    privacy.lock("vault")
    return privacy.status()


@router.post("/backup")
def set_backup_password(data: PasswordSet) -> dict:
    return _apply("backup", data)


@router.post("/backup/unlock")
def unlock_backup(data: PasswordUnlock) -> dict:
    try:
        privacy.unlock("backup", data.password)
    except PermissionError as exc:
        raise_api_error(401, "password", str(exc))
    finally:
        data.password = ""
    return privacy.status()


@router.post("/backup/lock")
def lock_backup() -> dict:
    privacy.lock("backup")
    return privacy.status()
