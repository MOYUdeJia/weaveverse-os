"""Configuration values shared by the backend entry point and app factory."""

from __future__ import annotations

import os
import sys
from pathlib import Path


HOST = "0.0.0.0"
WINDOW_HOST = "127.0.0.1"
MIN_WIDTH = 1000
MIN_HEIGHT = 700


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _resource_dir() -> Path:
    if _frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def _user_data_dir() -> Path:
    override = os.getenv("WEAVEVERSE_DATA_DIR", "").strip()
    if override:
        return Path(override)
    if _frozen():
        roaming = os.getenv("APPDATA")
        if roaming:
            return Path(roaming) / "WeaveverseOS"
        return Path.home() / "AppData" / "Roaming" / "WeaveverseOS"
    return Path(__file__).resolve().parents[1] / "data"


BACKEND_DIR = _resource_dir()
PROJECT_ROOT = BACKEND_DIR if _frozen() else BACKEND_DIR.parent
FRONTEND_DIST = (BACKEND_DIR / "frontend" / "dist") if _frozen() else PROJECT_ROOT / "frontend" / "dist"
DATA_DIR = _user_data_dir()
PORT_FILE = DATA_DIR / ".weaveverse-port" if _frozen() else BACKEND_DIR / ".weaveverse-port"
DATABASE_PATH = DATA_DIR / "weaveverse.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
ATTACHMENTS_DIR = DATA_DIR / "attachments"
BOOKS_DIR = DATA_DIR / "books"
ICONS_DIR = DATA_DIR / "icons"
BACKGROUNDS_DIR = DATA_DIR / "backgrounds"
BACKUPS_DIR = DATA_DIR / "backups"
SPLASH_DIR = DATA_DIR / "splash"
THEMES_DIR = DATA_DIR / "themes"
ASSETS_DIR = DATA_DIR / "assets"
PRESETS_DIR = DATA_DIR / "presets"

DEV_SERVER_URL = os.getenv("WEAVEVERSE_DEV_SERVER_URL", "http://127.0.0.1:5173")


# 判断是否走 Vite 开发模式。
# Return true when the task-book development flag is enabled.
def is_dev_mode() -> bool:
    return os.getenv("WEAVEVERSE_DEV") == "1" and not _frozen()
