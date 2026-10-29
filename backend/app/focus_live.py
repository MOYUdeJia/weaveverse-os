"""In-memory focus clock shared by the main window and the desktop pet.

Both webviews talk to this process over HTTP. They do not share JavaScript
memory, and a second pywebview window is a separate browser profile for
script state. The countdown itself is one ends_at timestamp on this server.
"""

from __future__ import annotations

import threading
import time

FOCUS_SECONDS = 25 * 60

_lock = threading.Lock()
_status = "idle"
_total = FOCUS_SECONDS
_left = FOCUS_SECONDS
_ends_at = 0
_recorded = False


def _now() -> int:
    return int(time.time() * 1000)


def _remaining() -> int:
    if _status == "running" and _ends_at:
        return max(0, int(round((_ends_at - _now()) / 1000)))
    return max(0, int(_left))


def _payload() -> dict:
    return {
        "status": _status,
        "total": _total,
        "left": _remaining() if _status == "running" else _left,
        "ends_at": _ends_at if _status == "running" else 0,
    }


def _clear() -> None:
    global _status, _total, _left, _ends_at, _recorded
    _status = "idle"
    _total = FOCUS_SECONDS
    _left = FOCUS_SECONDS
    _ends_at = 0
    _recorded = False


def _begin() -> None:
    global _status, _total, _left, _ends_at, _recorded
    _total = FOCUS_SECONDS
    _left = FOCUS_SECONDS
    _ends_at = _now() + FOCUS_SECONDS * 1000
    _status = "running"
    _recorded = False


def _mark_done() -> bool:
    """Move a running clock to done. Return True when the session still needs writing."""
    global _status, _left, _ends_at, _recorded
    _status = "done"
    _left = 0
    _ends_at = 0
    if _recorded:
        return False
    _recorded = True
    return True


def _write_session() -> None:
    global _recorded
    from sqlmodel import Session

    from app.db import engine
    from app.timeline import record_focus

    try:
        with Session(engine) as session:
            record_focus(session, 25)
    except Exception:
        with _lock:
            _recorded = False
        raise


def snapshot() -> dict:
    write = False
    with _lock:
        if _status == "running" and _remaining() <= 0:
            write = _mark_done()
        elif _status == "done" and not _recorded:
            _recorded = True
            write = True
        payload = _payload()
    if write:
        _write_session()
    return payload


def apply_action(action: str) -> dict:
    """Apply one clock command. Unknown actions raise ValueError."""
    write = False
    with _lock:
        global _status, _left, _ends_at
        if action == "start":
            if _status == "paused":
                _ends_at = _now() + _left * 1000
                _status = "running"
            elif _status != "running":
                _begin()
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
            _clear()
        elif action == "complete":
            if _status == "running":
                write = _mark_done()
        elif action == "acknowledge":
            if _status == "done":
                _clear()
        else:
            raise ValueError("不认识这个动作")
        payload = _payload()
    if write:
        _write_session()
        with _lock:
            payload = _payload()
    return payload
