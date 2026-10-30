"""HTTP for the live focus clock, saved tomatoes, and the stats sheet."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, Response
from sqlmodel import Session

from app.db import get_session
from app.errors import raise_api_error
from app.focus_backgrounds import list_backgrounds, read_background, save_background
from app.focus_live import apply_action, snapshot
from app.focus_presets import create_preset, delete_presets, list_presets, reorder_presets, update_preset
from app.focus_stats import export_csv, summarize_focus
from app.timeline import record_focus


router = APIRouter(prefix="/focus", tags=["focus"])

_ACTIONS = {
    "start",
    "pause",
    "resume",
    "abandon",
    "complete",
    "acknowledge",
    "duration",
    "preset",
    "end_rest",
    "seen",
}


@router.get("/live")
def get_live() -> dict:
    return snapshot()


@router.post("/live")
def post_live(data: dict) -> dict:
    action = data.get("action") if isinstance(data, dict) else None
    if action not in _ACTIONS:
        raise_api_error(400, "action", "不认识这个动作")
    minutes = data.get("minutes") if isinstance(data, dict) else None
    try:
        return apply_action(action, minutes=minutes, extra=data or {})
    except ValueError as exc:
        raise_api_error(400, "action", str(exc))


@router.get("/presets")
def get_presets(session: Session = Depends(get_session)) -> dict:
    return {"items": list_presets(session)}


@router.post("/presets")
def post_preset(data: dict, session: Session = Depends(get_session)) -> dict:
    return create_preset(session, data or {})


@router.patch("/presets/{preset_id}")
def patch_preset(preset_id: int, data: dict, session: Session = Depends(get_session)) -> dict:
    try:
        return update_preset(session, preset_id, data or {})
    except ValueError as exc:
        raise_api_error(404, "preset", str(exc))


@router.post("/presets/delete")
def post_delete_presets(data: dict, session: Session = Depends(get_session)) -> dict:
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list):
        raise_api_error(400, "ids", "要给出要删除的番茄钟")
    return {"removed": delete_presets(session, ids)}


@router.post("/presets/reorder")
def post_reorder_presets(data: dict, session: Session = Depends(get_session)) -> dict:
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list):
        raise_api_error(400, "ids", "要给出排序")
    return {"items": reorder_presets(session, ids)}


@router.get("/stats")
def get_stats(start: str | None = None, end: str | None = None, session: Session = Depends(get_session)) -> dict:
    return summarize_focus(session, start, end)


@router.get("/stats.csv")
def get_stats_csv(start: str | None = None, end: str | None = None, session: Session = Depends(get_session)) -> Response:
    text = export_csv(session, start, end)
    return Response(
        content="\ufeff" + text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=focus.csv"},
    )


@router.post("/sessions")
def post_session(data: dict, session: Session = Depends(get_session)) -> dict:
    try:
        row = record_focus(
            session,
            int((data or {}).get("minutes") or 0),
            label=(data or {}).get("label") or "补记",
            category=(data or {}).get("category") or "",
            outcome="done",
        )
    except (TypeError, ValueError) as exc:
        raise_api_error(400, "minutes", str(exc))
    return {"id": row.id}


@router.get("/backgrounds")
def get_backgrounds() -> dict:
    return {"items": list_backgrounds()}


@router.post("/backgrounds")
async def post_background(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    try:
        return save_background(file.filename or "background.png", raw)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))


@router.get("/backgrounds/{name}")
def get_background_file(name: str) -> FileResponse:
    path = read_background(name)
    if path is None:
        raise_api_error(404, "file", "没有这张背景")
    return FileResponse(path)
