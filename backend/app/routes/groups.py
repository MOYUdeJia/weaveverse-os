"""HTTP routes for sidebar group CRUD and reorder."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import crud, group_crud
from app.db import get_session
from app.errors import raise_api_error
from app.group_crud import MissingOverview
from app.icon_files import release_icon
from app.schemas import GroupCreate, GroupDetail, GroupRead, GroupReorder, GroupUpdate


router = APIRouter(prefix="/groups", tags=["groups"])


# 组装分组详情，带上该分组的导航项。
# Build a group detail payload including its nav items.
def _detail(session: Session, group_id: int) -> dict:
    group = group_crud.get_group(session, group_id)
    if group is None:
        raise_api_error(404, "id", "分组不存在")
    try:
        payload = group_crud.group_to_dict(session, group)
    except MissingOverview:
        raise_api_error(500, "id", "分组缺少导览页")
    payload["nav_items"] = crud.list_nav_items(session, group_id=group.id)
    return payload


@router.get("", response_model=list[GroupRead])
# 返回分组列表和各自的导航项数量。
# Return groups with each group's nav item count.
def get_groups(session: Session = Depends(get_session)) -> list[dict]:
    try:
        return [group_crud.group_to_dict(session, group) for group in group_crud.list_groups(session)]
    except MissingOverview:
        raise_api_error(500, "id", "分组缺少导览页")


@router.post("", response_model=GroupDetail)
# 创建分组，并自动创建它的导览页。
# Create a group and its overview page.
def create_group(data: GroupCreate, session: Session = Depends(get_session)) -> dict:
    group = group_crud.create_group(session, data.name, data.icon, data.description)
    return _detail(session, group.id)


@router.post("/reorder", response_model=list[GroupRead])
# 按 id 数组重排分组。
# Reorder groups from an id array.
def reorder_groups(data: GroupReorder, session: Session = Depends(get_session)) -> list[dict]:
    if len(data.ids) != len(set(data.ids)):
        raise_api_error(400, "ids", "id 列表不能重复")

    groups = group_crud.list_groups(session)
    known_ids = {group.id for group in groups}
    missing = [group_id for group_id in data.ids if group_id not in known_ids]
    if missing:
        raise_api_error(400, "ids", "包含不存在的分组")
    if set(data.ids) != known_ids:
        raise_api_error(400, "ids", "必须包含全部分组 id")

    group_crud.reorder_groups(session, data.ids)
    try:
        return [group_crud.group_to_dict(session, group) for group in group_crud.list_groups(session)]
    except MissingOverview:
        raise_api_error(500, "id", "分组缺少导览页")


@router.get("/{group_id}", response_model=GroupDetail)
# 返回一个分组和它的导航项。
# Return one group and its nav items.
def get_group(group_id: int, session: Session = Depends(get_session)) -> dict:
    return _detail(session, group_id)


@router.patch("/{group_id}", response_model=GroupRead)
# 更新分组名字、图标或简介。系统分组不能改名。
# Update a group's name, icon, or description. The system group cannot be renamed.
def update_group(group_id: int, data: GroupUpdate, session: Session = Depends(get_session)):
    if data.name is None and data.icon is None and data.description is None:
        raise_api_error(400, "body", "没有要更新的字段")

    group = group_crud.get_group(session, group_id)
    if group is None:
        raise_api_error(404, "id", "分组不存在")
    if group.is_system and data.name is not None and data.name != group.name:
        raise_api_error(409, "name", "系统分组不能改名")

    previous_icon = group.icon
    try:
        updated = group_crud.update_group(
            session,
            group,
            name=data.name,
            icon=data.icon,
            description=data.description,
        )
    except MissingOverview:
        raise_api_error(500, "id", "分组缺少导览页")
    if previous_icon != updated.icon:
        release_icon(session, previous_icon)
    try:
        return group_crud.group_to_dict(session, updated)
    except MissingOverview:
        raise_api_error(500, "id", "分组缺少导览页")


@router.delete("/{group_id}")
# 删除分组及其导航项。系统分组不能删。
# Delete a group and its nav items. The system group cannot be deleted.
def delete_group(group_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    group = group_crud.get_group(session, group_id)
    if group is None:
        raise_api_error(404, "id", "分组不存在")
    if group.is_system:
        raise_api_error(409, "id", "系统分组不能删除")

    icons = group_crud.delete_group(session, group)
    for icon in icons:
        release_icon(session, icon)
    return {"status": "ok"}
