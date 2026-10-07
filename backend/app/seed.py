"""Initial database seed data for first-run M1 navigation."""

from __future__ import annotations

from sqlmodel import Session

from app.db import engine
from app.models import NavItem


DEFAULT_NAV_ITEMS = [
    {"title": "健身", "icon": "💪"},
    {"title": "学习", "icon": "📚"},
    {"title": "音乐", "icon": "🎵"},
    {"title": "游戏", "icon": "🎮"},
    {"title": "观后感", "icon": "🎬"},
    {"title": "未来规划", "icon": "🧭"},
]


# 仅在数据库文件首次创建时写入默认导航。
# Insert default sidebar entries only when the database file is first created.
def seed_initial_nav_items(should_seed: bool) -> None:
    if not should_seed:
        return

    with Session(engine) as session:
        for sort_order, item in enumerate(DEFAULT_NAV_ITEMS):
            session.add(NavItem(sort_order=sort_order, **item))
        session.commit()
