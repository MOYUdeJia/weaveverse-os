"""HTTP for the live focus clock. The pet window and the main window both use it."""

from __future__ import annotations

from fastapi import APIRouter

from app.errors import raise_api_error
from app.focus_live import apply_action, snapshot


router = APIRouter(prefix="/focus", tags=["focus"])

_ACTIONS = {"start", "pause", "resume", "abandon", "complete", "acknowledge"}


@router.get("/live")
def get_live() -> dict:
    return snapshot()


@router.post("/live")
def post_live(data: dict) -> dict:
    action = data.get("action") if isinstance(data, dict) else None
    if action not in _ACTIONS:
        raise_api_error(400, "action", "需要 start、pause、resume、abandon、complete 或 acknowledge")
    try:
        return apply_action(action)
    except ValueError as exc:
        raise_api_error(400, "action", str(exc))
