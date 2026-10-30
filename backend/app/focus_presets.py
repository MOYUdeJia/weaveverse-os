"""Saved tomato clocks. The sidebar list and the pet both read this table."""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import FocusPreset

CATEGORIES = ("学习", "工作", "生活")


def _clamp(value, low: int, high: int, fallback: int) -> int:
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return fallback
    if amount < low or amount > high:
        return fallback
    return amount


def _category(value: str) -> str:
    text = (value or "").strip()
    return text if text in CATEGORIES else "学习"


def ensure_presets(session: Session) -> None:
    existing = session.exec(select(FocusPreset.id)).first()
    if existing is not None:
        return
    session.add(
        FocusPreset(
            name="番茄",
            focus_minutes=25,
            rest_minutes=5,
            cycles=1,
            category="学习",
            sort_order=0,
        )
    )
    session.commit()


def _dump(row: FocusPreset) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "focus_minutes": row.focus_minutes,
        "rest_minutes": row.rest_minutes,
        "cycles": row.cycles,
        "category": row.category,
        "sort_order": row.sort_order,
    }


def list_presets(session: Session) -> list[dict]:
    ensure_presets(session)
    rows = session.exec(select(FocusPreset).order_by(FocusPreset.sort_order, FocusPreset.id)).all()
    return [_dump(row) for row in rows]


def create_preset(session: Session, data: dict) -> dict:
    ensure_presets(session)
    last = session.exec(select(FocusPreset).order_by(FocusPreset.sort_order.desc())).first()
    order = 0 if last is None else int(last.sort_order) + 1
    row = FocusPreset(
        name=((data or {}).get("name") or "番茄").strip()[:40] or "番茄",
        focus_minutes=_clamp((data or {}).get("focus_minutes"), 5, 180, 25),
        rest_minutes=_clamp((data or {}).get("rest_minutes"), 1, 60, 5),
        cycles=_clamp((data or {}).get("cycles"), 1, 12, 1),
        category=_category((data or {}).get("category")),
        sort_order=order,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _dump(row)


def update_preset(session: Session, preset_id: int, data: dict) -> dict:
    row = session.get(FocusPreset, preset_id)
    if row is None:
        raise ValueError("没有这个番茄钟")
    payload = data or {}
    if "name" in payload:
        row.name = (payload.get("name") or "番茄").strip()[:40] or "番茄"
    if "focus_minutes" in payload:
        row.focus_minutes = _clamp(payload.get("focus_minutes"), 5, 180, row.focus_minutes)
    if "rest_minutes" in payload:
        row.rest_minutes = _clamp(payload.get("rest_minutes"), 1, 60, row.rest_minutes)
    if "cycles" in payload:
        row.cycles = _clamp(payload.get("cycles"), 1, 12, row.cycles)
    if "category" in payload:
        row.category = _category(payload.get("category"))
    session.add(row)
    session.commit()
    session.refresh(row)
    return _dump(row)


def delete_presets(session: Session, ids: list[int]) -> int:
    removed = 0
    for preset_id in ids:
        row = session.get(FocusPreset, int(preset_id))
        if row is None:
            continue
        session.delete(row)
        removed += 1
    session.commit()
    ensure_presets(session)
    return removed


def reorder_presets(session: Session, ids: list[int]) -> list[dict]:
    for index, preset_id in enumerate(ids):
        row = session.get(FocusPreset, int(preset_id))
        if row is None:
            continue
        row.sort_order = index
        session.add(row)
    session.commit()
    return list_presets(session)
