"""Set and unlock the single security password."""

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


def _change(data: PasswordSet, session: Session) -> dict:
    try:
        vault_crud.change_security_password(session, data.password, data.current)
    except PermissionError as exc:
        raise_api_error(401, "current", str(exc))
    except ValueError as exc:
        raise_api_error(400, "password", str(exc))
    except Exception:
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
    return _change(data, session)


@router.post("/security")
def set_security_password(data: PasswordSet, session: Session = Depends(get_session)) -> dict:
    return _change(data, session)


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
