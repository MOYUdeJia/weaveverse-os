"""Configuration values shared by the backend entry point and app factory."""

from __future__ import annotations

import os
from pathlib import Path


HOST = "127.0.0.1"
MIN_WIDTH = 1000
MIN_HEIGHT = 700

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
PORT_FILE = BACKEND_DIR / ".weaveverse-port"
DATA_DIR = BACKEND_DIR / "data"
DATABASE_PATH = DATA_DIR / "weaveverse.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

DEV_SERVER_URL = os.getenv("WEAVEVERSE_DEV_SERVER_URL", "http://127.0.0.1:5173")


def is_dev_mode() -> bool:
    """Return true when the task-book development flag is enabled."""
    return os.getenv("WEAVEVERSE_DEV") == "1"

