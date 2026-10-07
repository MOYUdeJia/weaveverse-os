"""Request and response schemas for API boundaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class MarkdownContent(BaseModel):
    text: str = ""


class TodoItem(BaseModel):
    text: str
    done: bool = False


class TodoContent(BaseModel):
    items: list[TodoItem] = Field(default_factory=list)


class LinkItem(BaseModel):
    title: str
    url: str


class LinkContent(BaseModel):
    links: list[LinkItem] = Field(default_factory=list)


class GalleryImage(BaseModel):
    filename: str
    caption: str = ""


class GalleryContent(BaseModel):
    images: list[GalleryImage] = Field(default_factory=list)


BLOCK_CONTENT_MODELS = {
    "markdown": MarkdownContent,
    "todo": TodoContent,
    "link": LinkContent,
    "gallery": GalleryContent,
}


# 按区块类型校验 content；未知类型只要是对象就原样保存。
# Validate known block content; unknown types are stored as a JSON object.
def parse_block_content(block_type: str, content: Any) -> dict:
    if not isinstance(content, dict):
        raise ValueError("content 必须是 JSON 对象")

    model = BLOCK_CONTENT_MODELS.get(block_type)
    if model is None:
        return content

    try:
        return model.model_validate(content).model_dump()
    except ValidationError as exc:
        first = exc.errors()[0]
        field = str((first.get("loc") or ("content",))[-1])
        raise ValueError(f"{field}: {first.get('msg') or '内容格式错误'}") from exc


class NavItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    icon: str = Field(min_length=1, max_length=20)

    @field_validator("title", "icon")
    @classmethod
    # 去掉首尾空白，拒绝空字符串。
    # Strip surrounding whitespace and reject empty values.
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class NavItemCreate(NavItemBase):
    page_type: str = "markdown"

    @field_validator("page_type")
    @classmethod
    # 规范化页面类型字符串。
    # Normalize the page type string.
    def strip_page_type(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class NavItemUpdate(NavItemBase):
    pass


class NavItemRead(NavItemBase):
    id: int
    page_type: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class BlockRead(BaseModel):
    id: int
    nav_item_id: int
    block_type: str
    content: dict
    sort_order: int
    created_at: datetime
    updated_at: datetime


class NavItemDetail(NavItemRead):
    blocks: list[BlockRead] = Field(default_factory=list)


class NavReorder(BaseModel):
    ids: list[int]


class BlockCreate(BaseModel):
    block_type: str = Field(min_length=1, max_length=32)
    content: dict = Field(default_factory=dict)

    @field_validator("block_type")
    @classmethod
    # 规范化区块类型字符串。
    # Normalize the block type string.
    def strip_block_type(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class BlockUpdate(BaseModel):
    content: dict


class PageTypeRead(BaseModel):
    type: str
    label: str
    multi_instance: bool
