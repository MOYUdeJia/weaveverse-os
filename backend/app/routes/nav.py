"""HTTP routes for sidebar navigation CRUD, detail, blocks, and reorder."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app import crud, group_crud
from app.crud import TitleConflict
from app.db import get_session
from app.errors import raise_api_error
from app.icon_files import release_icon
from app.models import NavItem
from app.page_types import OVERVIEW_PAGE_TYPE, PAGE_TYPES, default_icon_for, is_focus_page
from app.schemas import (
    BlockCreate,
    NavItemCreate,
    NavItemDetail,
    NavItemPatch,
    NavItemRead,
    NavItemUpdate,
    NavReorder,
)
from app.templates import get_template


router = APIRouter(prefix="/nav", tags=["nav"])


# 单实例页面类型已经有一条时，拒绝再创建。
# Reject a second navigation item for a single-instance page type.
def _ensure_single_instance(session: Session, page_type: str) -> None:
    spec = PAGE_TYPES.get(page_type)
    if spec is None or spec["multi_instance"]:
        return
    existing = session.exec(select(NavItem.id).where(NavItem.page_type == page_type)).first()
    if existing is not None:
        raise_api_error(409, "page_type", "这个页面类型只能创建一个")


# 分组导览不走普通导航接口改删。
# Overview pages are not edited or deleted through the normal nav routes.
def _reject_overview(item: NavItem) -> None:
    if item.page_type == OVERVIEW_PAGE_TYPE:
        raise_api_error(409, "id", "分组导览不能在这里修改")


# 单实例类型固定放进系统分组；其他类型缺省也进系统分组。
# Single-instance types always land in the system group. Others default there too.
def _resolve_group_id(session: Session, page_type: str, requested: int | None) -> int:
    system = group_crud.get_system_group(session)
    if system is None or system.id is None:
        raise_api_error(500, "group_id", "缺少系统分组")
    spec = PAGE_TYPES.get(page_type)
    if spec is not None and not spec["multi_instance"]:
        return system.id
    if requested is None:
        return system.id
    if group_crud.get_group(session, requested) is None:
        raise_api_error(400, "group_id", "分组不存在")
    return requested


# 没填图标时，专用页用注册表里的默认图标。其他类型仍必须自己填。
# Focus pages without an icon get the registry default. Other types must supply one.
def _apply_default_icon(data: NavItemCreate, page_type: str) -> None:
    if data.icon:
        return
    icon = default_icon_for(page_type)
    if not icon:
        raise_api_error(400, "icon", "请填写图标")
    data.icon = icon


# 单实例类型不能移出系统分组。
# Single-instance types cannot leave the system group.
def _ensure_can_move(session: Session, item: NavItem, group_id: int) -> None:
    if group_crud.get_group(session, group_id) is None:
        raise_api_error(400, "group_id", "分组不存在")
    spec = PAGE_TYPES.get(item.page_type)
    system = group_crud.get_system_group(session)
    if spec is not None and not spec["multi_instance"] and (system is None or group_id != system.id):
        raise_api_error(409, "group_id", "这个页面类型只能放在系统分组")


@router.get("", response_model=list[NavItemRead])
# 按排序返回导航列表。group_id 省略时返回全部分组。
# Return the ordered navigation list. Omit group_id to include every group.
def get_nav(
    group_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list:
    if group_id is not None and group_crud.get_group(session, group_id) is None:
        raise_api_error(404, "group_id", "分组不存在")
    return crud.list_nav_items(session, group_id=group_id)


@router.post("", response_model=NavItemDetail)
# 创建导航项并带上默认区块。
# Create a navigation item together with its default blocks.
def create_nav(data: NavItemCreate, session: Session = Depends(get_session)):
    if data.template_id and data.page_type:
        raise_api_error(400, "template_id", "不能同时指定 template_id 和 page_type")

    if data.template_id:
        spec = get_template(data.template_id)
        if spec is None:
            raise_api_error(400, "template_id", "未知的模板")
        if spec["page_type"] not in PAGE_TYPES:
            raise_api_error(400, "template_id", "模板的页面类型无效")
        if spec["page_type"] == OVERVIEW_PAGE_TYPE:
            raise_api_error(400, "template_id", "分组导览由系统创建，不能手动新建")
        _ensure_single_instance(session, spec["page_type"])
        _apply_default_icon(data, spec["page_type"])
        group_id = _resolve_group_id(session, spec["page_type"], data.group_id)
        try:
            item = crud.create_nav_item(
                session,
                data,
                page_type=spec["page_type"],
                group_id=group_id,
                default_blocks=spec["default_blocks"],
            )
        except TitleConflict:
            raise_api_error(409, "title", "同分组内已有同名导航项")
        except ValueError as exc:
            raise_api_error(400, "template_id", str(exc))
        return crud.nav_item_to_detail(session, item)

    page_type = data.page_type or "markdown"
    if page_type not in PAGE_TYPES:
        raise_api_error(400, "page_type", "未知的页面类型")
    if page_type == OVERVIEW_PAGE_TYPE:
        raise_api_error(400, "page_type", "分组导览由系统创建，不能手动新建")
    _ensure_single_instance(session, page_type)
    _apply_default_icon(data, page_type)
    group_id = _resolve_group_id(session, page_type, data.group_id)
    try:
        item = crud.create_nav_item(session, data, page_type=page_type, group_id=group_id)
    except TitleConflict:
        raise_api_error(409, "title", "同分组内已有同名导航项")
    except ValueError as exc:
        raise_api_error(400, "page_type", str(exc))
    return crud.nav_item_to_detail(session, item)


@router.post("/reorder", response_model=list[NavItemRead])
# 按 id 数组重排导航。
# Reorder navigation items from an id array.
def reorder_nav(data: NavReorder, session: Session = Depends(get_session)):
    if len(data.ids) != len(set(data.ids)):
        raise_api_error(400, "ids", "id 列表不能重复")

    if not data.ids:
        raise_api_error(400, "ids", "必须包含该分组的全部导航项 id")

    referenced = []
    for nav_id in data.ids:
        item = crud.get_nav_item(session, nav_id)
        if item is None or item.page_type == OVERVIEW_PAGE_TYPE:
            raise_api_error(400, "ids", "包含不存在的导航项")
        referenced.append(item)

    group_ids = {item.group_id for item in referenced}
    if len(group_ids) != 1:
        raise_api_error(400, "ids", "只能重排同一分组内的导航项")

    group_id = group_ids.pop()
    known_ids = {item.id for item in crud.list_nav_items(session, group_id=group_id)}
    if set(data.ids) != known_ids:
        raise_api_error(400, "ids", "必须包含该分组的全部导航项 id")

    return crud.reorder_nav_items(session, data.ids)


@router.get("/{nav_id}", response_model=NavItemDetail)
# 返回单个导航项及其区块。
# Return one navigation item and its blocks.
def get_nav_item(nav_id: int, session: Session = Depends(get_session)):
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    return crud.nav_item_to_detail(session, item)


@router.put("/{nav_id}", response_model=NavItemRead)
# 更新导航标题和图标。
# Update a navigation item's title and icon.
def update_nav(nav_id: int, data: NavItemUpdate, session: Session = Depends(get_session)):
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    _reject_overview(item)
    previous_icon = item.icon
    try:
        updated = crud.update_nav_item(session, item, data)
    except TitleConflict:
        raise_api_error(409, "title", "同分组内已有同名导航项")
    if previous_icon != updated.icon:
        release_icon(session, previous_icon)
    return updated


@router.patch("/{nav_id}", response_model=NavItemRead)
# 局部更新导航。改 group_id 就是移动到另一个分组。
# Partially update a nav item. Changing group_id moves it.
def patch_nav(nav_id: int, data: NavItemPatch, session: Session = Depends(get_session)):
    if data.title is None and data.icon is None and data.group_id is None:
        raise_api_error(400, "body", "没有要更新的字段")
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    _reject_overview(item)
    if data.group_id is not None and data.group_id != item.group_id:
        _ensure_can_move(session, item, data.group_id)
    previous_icon = item.icon
    try:
        updated = crud.update_nav_fields(
            session,
            item,
            title=data.title,
            icon=data.icon,
            group_id=data.group_id,
        )
    except TitleConflict:
        raise_api_error(409, "title", "同分组内已有同名导航项")
    if previous_icon != updated.icon:
        release_icon(session, previous_icon)
    return updated


@router.patch("/{nav_id}/pin", response_model=NavItemRead)
# 切换导航项置顶。
# Toggle whether a nav item is pinned.
def pin_nav(nav_id: int, session: Session = Depends(get_session)):
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    _reject_overview(item)
    return crud.toggle_pin(session, item)


@router.patch("/{nav_id}/lock", response_model=NavItemRead)
# 切换导航项锁定。
# Toggle whether a nav item is locked.
def lock_nav(nav_id: int, session: Session = Depends(get_session)):
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    _reject_overview(item)
    return crud.toggle_lock(session, item)


@router.delete("/{nav_id}")
# 删除导航项及其区块。
# Delete a navigation item and its blocks.
def delete_nav(nav_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    if item.page_type == OVERVIEW_PAGE_TYPE:
        raise_api_error(409, "id", "分组导览不能单独删除")
    if item.locked:
        raise_api_error(409, "id", "已锁定，不能删除")
    previous_icon = item.icon
    crud.delete_nav_item(session, item)
    release_icon(session, previous_icon)
    return {"status": "ok"}


@router.get("/{nav_id}/blocks", response_model=list)
# 返回某页的区块列表。
# Return the blocks that belong to a navigation item.
def get_nav_blocks(nav_id: int, session: Session = Depends(get_session)):
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    return [crud.block_to_dict(block) for block in crud.list_blocks(session, nav_id)]


@router.post("/{nav_id}/blocks")
# 给页面追加一个区块。
# Append a block to a navigation page.
def create_nav_block(nav_id: int, data: BlockCreate, session: Session = Depends(get_session)):
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    if is_focus_page(item.page_type):
        raise_api_error(409, "page_type", "专用页不能再添加区块")
    try:
        block = crud.create_block(session, nav_id, data)
    except ValueError as exc:
        raise_api_error(400, "content", str(exc))
    return crud.block_to_dict(block)
