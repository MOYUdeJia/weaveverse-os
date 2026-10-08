"""Database operations for navigation items and blocks."""

from __future__ import annotations

import json

from sqlmodel import Session, func, select

from app.models import Block, NavItem, utc_now
from app.page_types import OVERVIEW_PAGE_TYPE, PAGE_TYPES
from app.schemas import BlockCreate, BlockUpdate, NavItemCreate, NavItemUpdate, parse_block_content


class TitleConflict(Exception):
    """Raised when another item in the same group already uses this title."""


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


# 比较标题时去掉全部空白并忽略大小写。
# Compare titles with all whitespace removed and case folded.
def title_key(title: str) -> str:
    return "".join(title.split()).casefold()


# 同分组里是否已有相同标题。分组导览不参与比较。
# Return whether the group already has this title. Overviews are ignored.
def title_taken(session: Session, group_id: int, title: str, exclude_id: int | None = None) -> bool:
    key = title_key(title)
    statement = select(NavItem).where(
        NavItem.group_id == group_id,
        NavItem.page_type != OVERVIEW_PAGE_TYPE,
    )
    for item in session.exec(statement).all():
        if exclude_id is not None and item.id == exclude_id:
            continue
        if title_key(item.title) == key:
            return True
    return False


# 标题或分组真的变了才查重。历史重名在原样保存时放行。
# Check uniqueness only when the title or group actually changes.
def ensure_title_available(
    session: Session,
    group_id: int,
    title: str,
    *,
    exclude_id: int | None = None,
    current_title: str | None = None,
    current_group_id: int | None = None,
) -> None:
    unchanged = (
        exclude_id is not None
        and current_group_id == group_id
        and current_title is not None
        and title_key(current_title) == title_key(title)
    )
    if unchanged:
        return
    if title_taken(session, group_id, title, exclude_id=exclude_id):
        raise TitleConflict


# 列出用户可见的导航项，不含分组导览。置顶在前。
# List user-facing nav items, excluding overviews. Pinned items come first.
def list_nav_items(session: Session, group_id: int | None = None) -> list[NavItem]:
    statement = select(NavItem).where(NavItem.page_type != OVERVIEW_PAGE_TYPE)
    if group_id is not None:
        statement = statement.where(NavItem.group_id == group_id)
    statement = statement.order_by(NavItem.pinned.desc(), NavItem.sort_order, NavItem.id)
    return list(session.exec(statement).all())


# 取分组内下一条 sort_order，不含导览页。
# Next sort_order inside one group, ignoring the overview page.
def _next_sort_order(session: Session, group_id: int) -> int:
    max_order = session.exec(
        select(func.max(NavItem.sort_order)).where(
            NavItem.group_id == group_id,
            NavItem.page_type != OVERVIEW_PAGE_TYPE,
        )
    ).one()
    return 0 if max_order is None else int(max_order) + 1


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
    group_id: int,
    default_blocks: list[dict] | None = None,
) -> NavItem:
    ensure_title_available(session, group_id, data.title)
    blocks = PAGE_TYPES[page_type]["default_blocks"] if default_blocks is None else default_blocks
    item = NavItem(
        title=data.title,
        icon=data.icon,
        page_type=page_type,
        group_id=group_id,
        pinned=False,
        sort_order=_next_sort_order(session, group_id),
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


# 更新标题、图标，或把导航项移到另一个分组。
# Update title and icon, or move the item into another group.
def update_nav_fields(
    session: Session,
    item: NavItem,
    *,
    title: str | None = None,
    icon: str | None = None,
    group_id: int | None = None,
) -> NavItem:
    next_title = item.title if title is None else title
    next_group = item.group_id if group_id is None else group_id
    ensure_title_available(
        session,
        next_group,
        next_title,
        exclude_id=item.id,
        current_title=item.title,
        current_group_id=item.group_id,
    )
    if group_id is not None and group_id != item.group_id:
        item.group_id = group_id
        item.sort_order = _next_sort_order(session, group_id)
    if title is not None:
        item.title = title
    if icon is not None:
        item.icon = icon
    item.updated_at = utc_now()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


# 更新导航标题和图标。
# Update a navigation item's title and icon.
def update_nav_item(session: Session, item: NavItem, data: NavItemUpdate) -> NavItem:
    return update_nav_fields(session, item, title=data.title, icon=data.icon)


# 切换置顶。置顶排到分组最前，取消后排到分组末尾。
# Toggle pin. Pinning moves the item to the front; unpinning sends it to the end.
def toggle_pin(session: Session, item: NavItem) -> NavItem:
    if item.pinned:
        item.pinned = False
        item.sort_order = _next_sort_order(session, item.group_id)
    else:
        item.pinned = True
        min_order = session.exec(
            select(func.min(NavItem.sort_order)).where(
                NavItem.group_id == item.group_id,
                NavItem.page_type != OVERVIEW_PAGE_TYPE,
            )
        ).one()
        item.sort_order = 0 if min_order is None else int(min_order) - 1
    item.updated_at = utc_now()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


# 切换导航项锁定。锁定后不能删除，标题和图标仍可改。
# Toggle the nav lock. A locked item cannot be deleted, but its title and icon can change.
def toggle_lock(session: Session, item: NavItem) -> NavItem:
    item.locked = not item.locked
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
    group_id = by_id[ids[0]].group_id if ids else None

    for index, nav_id in enumerate(ids):
        item = by_id[nav_id]
        item.sort_order = index
        item.updated_at = utc_now()
        session.add(item)

    session.commit()
    if group_id is None:
        return []
    return list_nav_items(session, group_id=group_id)


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
        "group_id": item.group_id,
        "pinned": item.pinned,
        "locked": item.locked,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "blocks": [block_to_dict(block) for block in list_blocks(session, item.id)],
    }
