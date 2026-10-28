"""Machine settings that do not belong in appearance.json."""

from __future__ import annotations

from fastapi import APIRouter

from app.autostart import autostart_enabled, set_autostart
from app.errors import raise_api_error


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/autostart")
def get_autostart() -> dict:
    return {"enabled": autostart_enabled()}


@router.put("/autostart")
def put_autostart(data: dict) -> dict:
    if not isinstance(data, dict) or "enabled" not in data:
        raise_api_error(400, "enabled", "需要 enabled")
    try:
        enabled = set_autostart(bool(data.get("enabled")))
    except ValueError as exc:
        raise_api_error(400, "enabled", str(exc))
    except OSError:
        raise_api_error(500, "enabled", "写不了启动项，请检查当前用户权限")
    return {"enabled": enabled}
