"""In-memory focus clock shared by the main window and the desktop pet.

Both webviews talk to this process over HTTP. The countdown is one ends_at
timestamp. A finished focus round is written, then the clock becomes the rest.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_status = "idle"
_phase = "focus"
_name = "番茄"
_category = "学习"
_preset_id = None
_focus_sec = 25 * 60
_rest_sec = 5 * 60
_cycles = 1
_cycle = 1
_total = 25 * 60
_left = 25 * 60
_ends_at = 0
_recorded = False
_notice = ""


def _now() -> int:
    return int(time.time() * 1000)


def _remaining() -> int:
    if _status == "running" and _ends_at:
        return max(0, int(round((_ends_at - _now()) / 1000)))
    return max(0, int(_left))


def _payload() -> dict:
    return {
        "status": _status,
        "phase": _phase,
        "total": _total,
        "left": _remaining() if _status == "running" else _left,
        "ends_at": _ends_at if _status == "running" else 0,
        "name": _name,
        "category": _category,
        "preset_id": _preset_id,
        "focus_minutes": max(1, int(round(_focus_sec / 60))),
        "rest_minutes": max(1, int(round(_rest_sec / 60))),
        "cycle": _cycle,
        "cycles": _cycles,
        "notice": _notice,
    }


def _arm(seconds: int, phase: str) -> None:
    global _status, _phase, _total, _left, _ends_at, _recorded
    _phase = phase
    _total = seconds
    _left = seconds
    _ends_at = _now() + seconds * 1000
    _status = "running"
    _recorded = False


def _idle_face() -> None:
    global _status, _phase, _total, _left, _ends_at, _recorded, _cycle
    _status = "idle"
    _phase = "focus"
    _cycle = 1
    _total = _focus_sec
    _left = _focus_sec
    _ends_at = 0
    _recorded = False


def _advance_after_rest() -> None:
    global _cycle, _notice
    if _cycle < _cycles:
        _cycle += 1
        _notice = ""
        _arm(_focus_sec, "focus")
        return
    _notice = ""
    _idle_face()


def _begin_rest() -> None:
    global _notice
    _notice = "rest"
    if _rest_sec >= 60:
        _arm(_rest_sec, "rest")
        return
    _advance_after_rest()


def _write_session(minutes: int, outcome: str, interrupt: str = "") -> None:
    from sqlmodel import Session

    from app.db import engine
    from app.timeline import record_focus

    label = _name if outcome == "done" else f"放弃了{_name}"
    with Session(engine) as db:
        record_focus(
            db,
            minutes,
            label=label,
            category=_category,
            outcome=outcome,
            interrupt=interrupt,
        )


def _finish_focus() -> tuple[int, str]:
    """The focus interval reached zero. Rest starts after the write."""
    minutes = max(1, int(round(_focus_sec / 60)))
    _begin_rest()
    return minutes, "done"


def snapshot() -> dict:
    write = None
    with _lock:
        if _status == "running" and _remaining() <= 0:
            if _phase == "focus" and not _recorded:
                write = _finish_focus()
            elif _phase == "rest":
                _advance_after_rest()
        payload = _payload()
    if write is not None:
        _write_session(write[0], write[1])
        with _lock:
            payload = _payload()
    return payload


def _apply_preset_locked(data: dict) -> None:
    global _name, _category, _preset_id, _focus_sec, _rest_sec, _cycles
    if _status == "running":
        raise ValueError("这一轮还在走，先暂停再换番茄钟")
    focus = int(data.get("focus_minutes") or 25)
    rest = int(data.get("rest_minutes") or 5)
    cycles = int(data.get("cycles") or 1)
    if focus < 5 or focus > 180:
        raise ValueError("专注要在 5 到 180 分钟之间")
    if rest < 1 or rest > 60:
        raise ValueError("休息要在 1 到 60 分钟之间")
    if cycles < 1 or cycles > 12:
        raise ValueError("循环要在 1 到 12 次之间")
    _name = str(data.get("name") or "番茄")[:40]
    _category = str(data.get("category") or "学习")[:20]
    _preset_id = data.get("preset_id")
    _focus_sec = focus * 60
    _rest_sec = rest * 60
    _cycles = cycles
    _idle_face()


def apply_action(action: str, minutes: int | None = None, extra: dict | None = None) -> dict:
    """Apply one clock command. Unknown actions raise ValueError."""
    extra = extra or {}
    write = None
    with _lock:
        global _status, _left, _ends_at, _notice
        if action == "start":
            if _status == "paused":
                _ends_at = _now() + _left * 1000
                _status = "running"
            elif _status != "running":
                _arm(_focus_sec, "focus")
        elif action == "pause":
            if _status == "running":
                _left = _remaining()
                _ends_at = 0
                _status = "paused"
        elif action == "resume":
            if _status == "paused":
                _ends_at = _now() + max(0, _left) * 1000
                _status = "running"
        elif action == "abandon":
            if extra.get("record") and _phase == "focus" and _status in {"running", "paused"}:
                spent = _remaining() if _status == "running" else _left
                used = max(1, int(round((_focus_sec - spent) / 60)))
                write = (used, "abandoned", str(extra.get("interrupt") or "")[:40])
            _notice = ""
            _idle_face()
        elif action == "complete":
            if _status == "running" and _phase == "focus":
                write = (*_finish_focus(), "")
        elif action == "end_rest":
            if _phase == "rest":
                _advance_after_rest()
        elif action == "acknowledge":
            _notice = ""
            if _status == "done":
                _idle_face()
        elif action == "duration":
            _apply_preset_locked(
                {
                    "name": _name,
                    "category": _category,
                    "preset_id": _preset_id,
                    "focus_minutes": 25 if minutes is None else minutes,
                    "rest_minutes": max(1, int(round(_rest_sec / 60))),
                    "cycles": _cycles,
                }
            )
        elif action == "preset":
            _apply_preset_locked(extra)
        elif action == "seen":
            _notice = ""
        else:
            raise ValueError("不认识这个动作")
        payload = _payload()
    if write is not None:
        _write_session(write[0], write[1], write[2] if len(write) > 2 else "")
        with _lock:
            payload = _payload()
    return payload
