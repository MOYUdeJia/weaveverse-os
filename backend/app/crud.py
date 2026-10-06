"""Database operations for navigation items."""
#只做数据操作：查/增/改/删
from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, func, select

from app.models import NavItem
from app.schemas import NavItemCreate, NavItemUpdate


def list_nav_items(session: Session) -> list[NavItem]:
    statement = select(NavItem).order_by(NavItem.sort_order, NavItem.id)
    return list(session.exec(statement).all())


def get_nav_item(session: Session, nav_id: int) -> NavItem | None:
    return session.get(NavItem, nav_id)


def create_nav_item(session: Session, data: NavItemCreate) -> NavItem:
    max_order = session.exec(select(func.max(NavItem.sort_order))).one()
    next_order = 0 if max_order is None else int(max_order) + 1
    item = NavItem(title=data.title, icon=data.icon, sort_order=next_order)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def update_nav_item(session: Session, item: NavItem, data: NavItemUpdate) -> NavItem:
    item.title = data.title
    item.icon = data.icon
    item.updated_at = datetime.utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def delete_nav_item(session: Session, item: NavItem) -> None:
    session.delete(item)
    session.commit()
