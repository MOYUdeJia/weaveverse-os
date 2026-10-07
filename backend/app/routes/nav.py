"""HTTP routes for sidebar navigation CRUD, detail, blocks, and reorder."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import crud
from app.db import get_session
from app.errors import raise_api_error
from app.page_types import PAGE_TYPES
from app.schemas import BlockCreate, NavItemCreate, NavItemDetail, NavItemRead, NavItemUpdate, NavReorder


router = APIRouter(prefix="/nav", tags=["nav"])


@router.get("", response_model=list[NavItemRead])
# 按排序返回导航列表。
# Return the ordered navigation list.
def get_nav(session: Session = Depends(get_session)) -> list:
    return crud.list_nav_items(session)


@router.post("", response_model=NavItemDetail)
# 创建导航项并带上默认区块。
# Create a navigation item together with its default blocks.
def create_nav(data: NavItemCreate, session: Session = Depends(get_session)):
    if data.page_type not in PAGE_TYPES:
        raise_api_error(400, "page_type", "未知的页面类型")
    try:
        item = crud.create_nav_item(session, data)
    except ValueError as exc:
        raise_api_error(400, "page_type", str(exc))
    return crud.nav_item_to_detail(session, item)


@router.post("/reorder", response_model=list[NavItemRead])
# 按 id 数组重排导航。
# Reorder navigation items from an id array.
def reorder_nav(data: NavReorder, session: Session = Depends(get_session)):
    if len(data.ids) != len(set(data.ids)):
        raise_api_error(400, "ids", "id 列表不能重复")

    items = crud.list_nav_items(session)
    known_ids = {item.id for item in items}
    missing = [nav_id for nav_id in data.ids if nav_id not in known_ids]
    if missing:
        raise_api_error(400, "ids", "包含不存在的导航项")
    if set(data.ids) != known_ids:
        raise_api_error(400, "ids", "必须包含全部导航项 id")

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
    return crud.update_nav_item(session, item, data)


@router.delete("/{nav_id}")
# 删除导航项及其区块。
# Delete a navigation item and its blocks.
def delete_nav(nav_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise_api_error(404, "id", "导航项不存在")
    crud.delete_nav_item(session, item)
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
    try:
        block = crud.create_block(session, nav_id, data)
    except ValueError as exc:
        raise_api_error(400, "content", str(exc))
    return crud.block_to_dict(block)
