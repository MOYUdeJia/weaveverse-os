"""HTTP API routes for M0.

M0 keeps navigation data static here. M1 can replace this module's data source
with SQLite without changing the frontend contract.
"""

from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(prefix="/api")

NAV_ITEMS = [
    {"id": "fitness", "title": "健身", "icon": "💪"},
    {"id": "study", "title": "学习", "icon": "📚"},
    {"id": "music", "title": "音乐", "icon": "🎵"},
    {"id": "game", "title": "游戏", "icon": "🎮"},
    {"id": "review", "title": "观后感", "icon": "🎬"},
    {"id": "future", "title": "未来规划", "icon": "🧭"},
]


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/nav")
def get_nav() -> list[dict[str, str]]:
    return NAV_ITEMS
