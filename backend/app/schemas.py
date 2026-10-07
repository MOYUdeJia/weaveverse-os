"""Request and response schemas for API boundaries.

Known block types are validated here. M3 adds schedule, progress, and chart
without changing the database: they are still JSON inside Block.content.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, ValidationError, field_validator


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


# 拒绝布尔和字符串，保留 int/float 原样，避免 1 变成 1.0。
# Reject bools and strings, and keep int/float values unchanged.
def _finite_number(value: Any) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("必须是数字")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("必须是有限数字")
    return value


Number = Annotated[int | float, BeforeValidator(_finite_number)]


class ScheduleEntry(BaseModel):
    date: str
    title: str
    done: bool = False
    note: str = ""

    @field_validator("date")
    @classmethod
    # 只接受日历日期，不接受时间。
    # Accept a calendar date and reject datetimes.
    def check_date(cls, value: str) -> str:
        stripped = value.strip()
        try:
            datetime.strptime(stripped, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("日期须为 YYYY-MM-DD") from exc
        return stripped

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class ScheduleContent(BaseModel):
    entries: list[ScheduleEntry] = Field(default_factory=list)


class ProgressItem(BaseModel):
    label: str
    current: Number = 0
    total: Number = 100
    unit: str = "%"

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class ProgressContent(BaseModel):
    items: list[ProgressItem] = Field(default_factory=list)


class ChartPoint(BaseModel):
    label: str
    value: Number

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class ChartContent(BaseModel):
    chart_type: Literal["line", "bar"]
    unit: str = ""
    data: list[ChartPoint] = Field(default_factory=list)


BLOCK_CONTENT_MODELS = {
    "markdown": MarkdownContent,
    "todo": TodoContent,
    "link": LinkContent,
    "gallery": GalleryContent,
    "schedule": ScheduleContent,
    "progress": ProgressContent,
    "chart": ChartContent,
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
    page_type: str | None = None
    template_id: str | None = None

    @field_validator("page_type", "template_id")
    @classmethod
    # 空白当未传；真正的空字符串拒绝。省略两者时由路由默认 markdown。
    # Treat blank as omitted, and reject an empty string. The route defaults to markdown.
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
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


class TemplateRead(BaseModel):
    id: str
    label: str
    description: str
    icon: str
    page_type: str
    block_count: int
