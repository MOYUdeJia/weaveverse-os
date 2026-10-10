"""Database operations for sidebar groups.

Each group owns its navigation items and exactly one group_overview page.
The system group is created by migration and cannot be deleted or renamed.
"""

from __future__ import annotations

from sqlmodel import Session, func, select

from app.models import Group, NavItem, utc_now
from app.page_types import OVERVIEW_PAGE_TYPE


SYSTEM_GROUP_NAME = "系统"
SYSTEM_GROUP_ICON = "⚙️"


class MissingOverview(Exception):
    """Raised when a group has no group_overview row."""


# 读取系统分组。迁移后应当始终存在。
# Load the system group. It should always exist after migration.
def get_system_group(session: Session) -> Group | None:
    statement = select(Group).where(Group.is_system == True)  # noqa: E712
    return session.exec(statement).first()


# 按主键读取分组。
# Load one group by primary key.
def get_group(session: Session, group_id: int) -> Group | None:
    return session.get(Group, group_id)


# 按 sort_order 列出全部分组。
# List every group ordered by sort_order.
def list_groups(session: Session) -> list[Group]:
    statement = select(Group).order_by(Group.sort_order, Group.id)
    return list(session.exec(statement).all())


# 读取分组的导览页。
# Load the overview page that belongs to a group.
def get_overview(session: Session, group_id: int) -> NavItem | None:
    statement = select(NavItem).where(
        NavItem.group_id == group_id,
        NavItem.page_type == OVERVIEW_PAGE_TYPE,
    )
    return session.exec(statement).first()


# 统计分组里用户可见的导航项，不含导览页。
# Count user-facing nav items in a group, excluding the overview.
def count_nav_items(session: Session, group_id: int) -> int:
    statement = (
        select(func.count())
        .select_from(NavItem)
        .where(
            NavItem.group_id == group_id,
            NavItem.page_type != OVERVIEW_PAGE_TYPE,
        )
    )
    return int(session.exec(statement).one())


# 把分组收成 API 字典。缺导览页时抛错。
# Build the API payload for a group. Raise when its overview is missing.
def group_to_dict(session: Session, group: Group) -> dict:
    overview = get_overview(session, group.id)
    if overview is None or overview.id is None:
        raise MissingOverview
    return {
        "id": group.id,
        "name": group.name,
        "icon": group.icon,
        "description": group.description,
        "is_system": group.is_system,
        "locked": group.locked,
        "sort_order": group.sort_order,
        "item_count": count_nav_items(session, group.id),
        "overview_id": overview.id,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


# 新建分组，并自动插入一条空的分组导览。
# Create a group and insert its empty overview page.
def create_group(session: Session, name: str, icon: str, description: str = "") -> Group:
    max_order = session.exec(select(func.max(Group.sort_order))).one()
    next_order = 0 if max_order is None else int(max_order) + 1
    group = Group(
        name=name,
        icon=icon,
        description=description,
        is_system=False,
        sort_order=next_order,
    )
    session.add(group)
    session.flush()
    session.add(
        NavItem(
            title=name,
            icon=icon,
            page_type=OVERVIEW_PAGE_TYPE,
            group_id=group.id,
            pinned=False,
            sort_order=0,
        )
    )
    session.commit()
    session.refresh(group)
    return group


# 更新分组名字、图标或简介，并让导览页的标题和图标跟着走。
# Update name, icon, or description, and keep the overview title and icon in sync.
def update_group(
    session: Session,
    group: Group,
    *,
    name: str | None = None,
    icon: str | None = None,
    description: str | None = None,
) -> Group:
    overview = get_overview(session, group.id)
    if overview is None:
        raise MissingOverview
    if name is not None:
        group.name = name
        overview.title = name
    if icon is not None:
        group.icon = icon
        overview.icon = icon
    if description is not None:
        group.description = description
    now = utc_now()
    group.updated_at = now
    overview.updated_at = now
    session.add(group)
    session.add(overview)
    session.commit()
    session.refresh(group)
    return group


# 切换分组锁定。锁定后不能删除，仍可以改名字、图标和简介。
# Toggle the group lock. A locked group cannot be deleted, but it can still be edited.
def toggle_group_lock(session: Session, group: Group) -> Group:
    group.locked = not group.locked
    group.updated_at = utc_now()
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


# 删除分组及其导航项，返回删除前引用过的图标。
# Delete a group and its nav items, and return icons referenced beforehand.
def delete_group(session: Session, group: Group) -> list[str]:
    items = list(session.exec(select(NavItem).where(NavItem.group_id == group.id)).all())
    icons = [group.icon, *[item.icon for item in items]]
    for item in items:
        session.delete(item)
    # 先删导航，再删分组。否则外键级联会先删掉行，ORM 再删一次就会报 0 行。
    # Delete nav rows before the group so cascade does not remove them twice.
    session.flush()
    session.delete(group)
    session.commit()
    return icons


# 按请求里的 id 顺序重写分组 sort_order。
# Rewrite group sort_order to match the requested id sequence.
def reorder_groups(session: Session, ids: list[int]) -> list[Group]:
    groups = list_groups(session)
    by_id = {group.id: group for group in groups}
    system = next((group for group in groups if group.is_system), None)
    ordered = [group_id for group_id in ids if system is None or group_id != system.id]
    if system is not None and system.id is not None:
        ordered.insert(0, system.id)
    now = utc_now()
    for index, group_id in enumerate(ordered):
        group = by_id[group_id]
        group.sort_order = index
        group.updated_at = now
        session.add(group)
    session.commit()
    return list_groups(session)
