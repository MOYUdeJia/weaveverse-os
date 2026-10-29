"""Machine settings that do not belong in appearance.json."""

from __future__ import annotations

from fastapi import APIRouter

from app.autostart import autostart_enabled, set_autostart
from app.data_move import describe_data_dir, move_data_dir
from app.errors import raise_api_error
from app.version import APP_VERSION, database_revision


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def get_status() -> dict:
    try:
        revision = database_revision()
    except Exception:
        revision = "读不到"
    return {"version": APP_VERSION, "revision": revision}


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


@router.get("/data-dir")
def get_data_dir() -> dict:
    return describe_data_dir()


@router.post("/data-dir")
def post_data_dir(data: dict) -> dict:
    path = data.get("path") if isinstance(data, dict) else None
    if not isinstance(path, str) or not path.strip():
        raise_api_error(400, "path", "需要新的数据目录")
    try:
        return move_data_dir(path)
    except ValueError as exc:
        raise_api_error(400, "path", str(exc))
    except OSError:
        raise_api_error(500, "path", "复制数据时出错，原来的目录还在")
