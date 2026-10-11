"""Scan and delete attachment files that nothing references."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.attachment_gc import purge_files, unused_files
from app.db import get_session

router = APIRouter(prefix="/cleanup", tags=["cleanup"])


class PurgeBody(BaseModel):
    filenames: list[str] = Field(default_factory=list)


@router.get("/attachments")
def list_unused(session: Session = Depends(get_session)) -> dict:
    items = unused_files(session)
    return {"items": items, "count": len(items)}


@router.post("/attachments")
def purge_unused(data: PurgeBody, session: Session = Depends(get_session)) -> dict:
    removed = purge_files(session, data.filenames)
    leftover = unused_files(session)
    return {"removed": removed, "items": leftover}
