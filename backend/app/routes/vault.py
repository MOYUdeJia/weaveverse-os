"""HTTP routes for the password vault. Ciphertext never leaves as plaintext until unlock."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app import vault_crud
from app.db import get_session
from app.errors import raise_api_error
from app.privacy import require_session

router = APIRouter(prefix="/vault", tags=["vault"])


class SectionWrite(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class Reorder(BaseModel):
    ids: list[int] = Field(min_length=1)
    section_id: int | None = None


class EntryWrite(BaseModel):
    section_id: int
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(default="", max_length=500)
    username: str = Field(default="", max_length=200)
    password: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=2000)


class EntryPatch(BaseModel):
    section_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    url: str | None = Field(default=None, max_length=500)
    username: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)
    pinned: bool | None = None
    locked: bool | None = None


def _unlocked() -> None:
    try:
        require_session("vault")
    except PermissionError as exc:
        raise_api_error(401, "password", str(exc))


@router.get("/count")
def vault_count(session: Session = Depends(get_session)) -> dict[str, int]:
    return {"count": vault_crud.count_entries(session)}


@router.get("/sections")
def list_sections(session: Session = Depends(get_session)) -> list[dict]:
    _unlocked()
    return [vault_crud.section_to_dict(row) for row in vault_crud.list_sections(session)]


@router.post("/sections")
def create_section(data: SectionWrite, session: Session = Depends(get_session)) -> dict:
    _unlocked()
    row = vault_crud.create_section(session, data.name.strip())
    return vault_crud.section_to_dict(row)


@router.patch("/sections/{section_id}")
def rename_section(section_id: int, data: SectionWrite, session: Session = Depends(get_session)) -> dict:
    _unlocked()
    row = vault_crud.get_section(session, section_id)
    if row is None:
        raise_api_error(404, "id", "分区不存在")
    updated = vault_crud.rename_section(session, row, data.name.strip())
    return vault_crud.section_to_dict(updated)


@router.delete("/sections/{section_id}")
def delete_section(section_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    _unlocked()
    row = vault_crud.get_section(session, section_id)
    if row is None:
        raise_api_error(404, "id", "分区不存在")
    vault_crud.delete_section(session, row)
    return {"status": "ok"}


@router.post("/sections/reorder")
def reorder_sections(data: Reorder, session: Session = Depends(get_session)) -> list[dict]:
    _unlocked()
    return [vault_crud.section_to_dict(row) for row in vault_crud.reorder_sections(session, data.ids)]


@router.get("/entries")
def list_entries(session: Session = Depends(get_session)) -> list[dict]:
    _unlocked()
    return [vault_crud.entry_to_dict(row) for row in vault_crud.list_entries(session)]


@router.post("/entries")
def create_entry(data: EntryWrite, session: Session = Depends(get_session)) -> dict:
    _unlocked()
    if vault_crud.get_section(session, data.section_id) is None:
        raise_api_error(404, "section_id", "分区不存在")
    row = vault_crud.create_entry(
        session,
        section_id=data.section_id,
        name=data.name.strip(),
        url=data.url.strip(),
        username=data.username.strip(),
        password=data.password,
        note=data.note.strip(),
    )
    data.password = ""
    return vault_crud.entry_to_dict(row)


@router.patch("/entries/{entry_id}")
def update_entry(entry_id: int, data: EntryPatch, session: Session = Depends(get_session)) -> dict:
    _unlocked()
    row = vault_crud.get_entry(session, entry_id)
    if row is None:
        raise_api_error(404, "id", "条目不存在")
    if data.section_id is not None and vault_crud.get_section(session, data.section_id) is None:
        raise_api_error(404, "section_id", "分区不存在")
    updated = vault_crud.update_entry(
        session,
        row,
        section_id=data.section_id,
        name=None if data.name is None else data.name.strip(),
        url=None if data.url is None else data.url.strip(),
        username=None if data.username is None else data.username.strip(),
        password=data.password,
        note=None if data.note is None else data.note.strip(),
        pinned=data.pinned,
        locked=data.locked,
    )
    data.password = None
    return vault_crud.entry_to_dict(updated)


@router.post("/entries/{entry_id}/top")
def pin_entry_top(entry_id: int, session: Session = Depends(get_session)) -> dict:
    _unlocked()
    row = vault_crud.get_entry(session, entry_id)
    if row is None:
        raise_api_error(404, "id", "条目不存在")
    return vault_crud.entry_to_dict(vault_crud.pin_to_top(session, row))


@router.post("/entries/reorder")
def reorder_entries(data: Reorder, session: Session = Depends(get_session)) -> list[dict]:
    _unlocked()
    if data.section_id is None:
        raise_api_error(400, "section_id", "缺少分区")
    return [vault_crud.entry_to_dict(row) for row in vault_crud.reorder_entries(session, data.section_id, data.ids)]


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    _unlocked()
    row = vault_crud.get_entry(session, entry_id)
    if row is None:
        raise_api_error(404, "id", "条目不存在")
    vault_crud.delete_entry(session, row)
    return {"status": "ok"}
