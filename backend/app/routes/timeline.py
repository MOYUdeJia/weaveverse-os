"""HTTP routes for the global timeline and finished focus intervals."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.errors import raise_api_error
from app.timeline import ensure_timeline_page, list_events, record_focus


router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("")
def get_timeline(session: Session = Depends(get_session)) -> dict:
    page = ensure_timeline_page(session)
    return {
        "nav_id": page.id,
        "group_id": page.group_id,
        "events": list_events(session),
    }


@router.post("/focus", status_code=201)
def post_focus(data: dict, session: Session = Depends(get_session)) -> dict:
    raw = data.get("minutes") if isinstance(data, dict) else None
    try:
        minutes = int(raw)
    except (TypeError, ValueError):
        minutes = 0
    if minutes < 5 or minutes > 180:
        raise_api_error(400, "minutes", "时长要在 5 到 180 分钟之间")
    try:
        row = record_focus(session, minutes)
    except ValueError as exc:
        raise_api_error(400, "minutes", str(exc))
    return {
        "id": row.id,
        "minutes": row.minutes,
        "label": row.label,
        "completed_at": row.completed_at,
    }
