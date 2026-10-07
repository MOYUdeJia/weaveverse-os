"""Database operations for navigation items and blocks."""

from __future__ import annotations

import json

from sqlmodel import Session, func, select

from app.models import Block, NavItem, utc_now
from app.page_types import PAGE_TYPES
from app.schemas import BlockCreate, BlockUpdate, NavItemCreate, NavItemUpdate, parse_block_content


# 把区块 content 编码成 SQLite TEXT。
# Encode block content as a SQLite TEXT JSON string.
def _dump_content(content: dict) -> str:
    return json.dumps(content, ensure_ascii=False)


# 把数据库里的 JSON 字符串解码成对象。
# Decode a stored JSON string into an object.
def _load_content(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


# 按 sort_order 列出全部导航项。
# List all navigation items ordered by sort_order.
def list_nav_items(session: Session) -> list[NavItem]:
    statement = select(NavItem).order_by(NavItem.sort_order, NavItem.id)
    return list(session.exec(statement).all())


# 按主键读取一条导航。
# Load one navigation item by primary key.
def get_nav_item(session: Session, nav_id: int) -> NavItem | None:
    return session.get(NavItem, nav_id)


# 创建导航项，并插入页面类型或模板给出的默认区块。
# Create a navigation item and insert page-type or template default blocks.
def create_nav_item(
    session: Session,
    data: NavItemCreate,
    *,
    page_type: str,
    default_blocks: list[dict] | None = None,
) -> NavItem:
    blocks = PAGE_TYPES[page_type]["default_blocks"] if default_blocks is None else default_blocks
    max_order = session.exec(select(func.max(NavItem.sort_order))).one()
    next_order = 0 if max_order is None else int(max_order) + 1
    item = NavItem(
        title=data.title,
        icon=data.icon,
        page_type=page_type,
        sort_order=next_order,
    )
    session.add(item)
    session.flush()

    for index, block in enumerate(blocks):
        content = parse_block_content(block["block_type"], block["content"])
        session.add(
            Block(
                nav_item_id=item.id,
                block_type=block["block_type"],
                content=_dump_content(content),
                sort_order=index,
            )
        )

    session.commit()
    session.refresh(item)
    return item


# 更新导航标题和图标。
# Update a navigation item's title and icon.
def update_nav_item(session: Session, item: NavItem, data: NavItemUpdate) -> NavItem:
    item.title = data.title
    item.icon = data.icon
    item.updated_at = utc_now()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


# 删除导航项；依赖外键级联删掉它的区块。
# Delete a navigation item; FK cascade removes its blocks.
def delete_nav_item(session: Session, item: NavItem) -> None:
    session.delete(item)
    session.commit()


# 按请求里的 id 顺序重写 sort_order。
# Rewrite sort_order to match the requested id sequence.
def reorder_nav_items(session: Session, ids: list[int]) -> list[NavItem]:
    items = list_nav_items(session)
    by_id = {item.id: item for item in items}

    for index, nav_id in enumerate(ids):
        item = by_id[nav_id]
        item.sort_order = index
        item.updated_at = utc_now()
        session.add(item)

    session.commit()
    return list_nav_items(session)


# 列出某页的全部区块。
# List every block that belongs to a navigation item.
def list_blocks(session: Session, nav_item_id: int) -> list[Block]:
    statement = (
        select(Block)
        .where(Block.nav_item_id == nav_item_id)
        .order_by(Block.sort_order, Block.id)
    )
    return list(session.exec(statement).all())


# 按主键读取一个区块。
# Load one block by primary key.
def get_block(session: Session, block_id: int) -> Block | None:
    return session.get(Block, block_id)


# 在页面底部追加一个区块。
# Append a block at the bottom of a page.
def create_block(session: Session, nav_item_id: int, data: BlockCreate) -> Block:
    content = parse_block_content(data.block_type, data.content)
    max_order = session.exec(
        select(func.max(Block.sort_order)).where(Block.nav_item_id == nav_item_id)
    ).one()
    next_order = 0 if max_order is None else int(max_order) + 1
    block = Block(
        nav_item_id=nav_item_id,
        block_type=data.block_type,
        content=_dump_content(content),
        sort_order=next_order,
    )
    session.add(block)
    session.commit()
    session.refresh(block)
    return block


# 更新区块内容。
# Update a block's content payload.
def update_block(session: Session, block: Block, data: BlockUpdate) -> Block:
    content = parse_block_content(block.block_type, data.content)
    block.content = _dump_content(content)
    block.updated_at = utc_now()
    session.add(block)
    session.commit()
    session.refresh(block)
    return block


# 删除一个区块。
# Delete one block.
def delete_block(session: Session, block: Block) -> None:
    session.delete(block)
    session.commit()


# 把数据库区块转成 API 用的字典。
# Convert a stored block into an API-facing dictionary.
def block_to_dict(block: Block) -> dict:
    return {
        "id": block.id,
        "nav_item_id": block.nav_item_id,
        "block_type": block.block_type,
        "content": _load_content(block.content),
        "sort_order": block.sort_order,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
    }


# 把导航项和它的区块组装成详情。
# Assemble a navigation item plus its blocks into a detail payload.
def nav_item_to_detail(session: Session, item: NavItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "icon": item.icon,
        "page_type": item.page_type,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "blocks": [block_to_dict(block) for block in list_blocks(session, item.id)],
    }
