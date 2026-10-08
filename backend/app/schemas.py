"""Request and response schemas for API boundaries.

Known block types are validated here. M3 adds schedule, progress, and chart
without changing the database: they are still JSON inside Block.content.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, field_validator


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


class PlainLine(BaseModel):
    text: str = ""
    color: str = ""

    @field_validator("color")
    @classmethod
    # 空字符串是默认墨色。自定义只收 #RRGGBB。
    # Empty means the default ink color. Custom colors are #RRGGBB only.
    def check_color(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            return ""
        if re.fullmatch(r"#[0-9a-fA-F]{6}", stripped) is None:
            raise ValueError("颜色须为 #RRGGBB")
        return stripped.lower()


class PlainTextContent(BaseModel):
    mode: Literal["numbered", "bullets"] = "numbered"
    lines: list[PlainLine] = Field(default_factory=lambda: [PlainLine()])


class BookmarkItem(BaseModel):
    title: str = ""
    url: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("title", "url")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("tags")
    @classmethod
    # 去掉 # 前缀和空标签，同一条里不重复。
    # Drop hash prefixes and blanks, and keep each tag once per item.
    def clean_tags(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for tag in value:
            text = str(tag).strip().lstrip("#").strip()
            if text and text not in cleaned:
                cleaned.append(text[:40])
        return cleaned[:12]


class BookmarkSection(BaseModel):
    name: str = "收藏"
    items: list[BookmarkItem] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        return stripped[:40] or "收藏"


class BookmarksContent(BaseModel):
    sections: list[BookmarkSection] = Field(default_factory=lambda: [BookmarkSection()])

    @field_validator("sections")
    @classmethod
    def ensure_section(cls, value: list[BookmarkSection]) -> list[BookmarkSection]:
        return value or [BookmarkSection()]


CODE_LANGUAGES = {"plain", "javascript", "python", "json", "html", "css", "sql", "markdown"}


class CodeContent(BaseModel):
    language: str = "plain"
    text: str = ""
    highlight: bool = False

    @field_validator("language")
    @classmethod
    def check_language(cls, value: str) -> str:
        language = value.strip().lower() or "plain"
        if language not in CODE_LANGUAGES:
            raise ValueError("不支持的语言")
        return language


class CanvasContent(BaseModel):
    """Fabric canvas JSON. Extra keys such as version and viewportTransform are kept."""

    model_config = ConfigDict(extra="allow")

    objects: list[Any] = Field(default_factory=list)


BLOCK_CONTENT_MODELS = {
    "markdown": MarkdownContent,
    "todo": TodoContent,
    "link": LinkContent,
    "gallery": GalleryContent,
    "schedule": ScheduleContent,
    "progress": ProgressContent,
    "chart": ChartContent,
    "plain_text": PlainTextContent,
    "bookmarks": BookmarksContent,
    "code": CodeContent,
    "canvas": CanvasContent,
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


# 去掉首尾空白，拒绝空字符串。
# Strip surrounding whitespace and reject empty values.
def strip_required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("不能为空")
    return stripped


# 上传图标是 @file: 加 12 位编号。普通 emoji 原样通过。
# Uploaded icons are @file: plus 12 hex chars. Plain emoji passes through.
def check_icon_ref(value: str) -> str:
    if value.startswith("@file:") and re.fullmatch(r"@file:[0-9a-f]{12}", value) is None:
        raise ValueError("图标引用无效")
    return value


class NavItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    icon: str = Field(min_length=1, max_length=20)

    @field_validator("title", "icon")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return strip_required_text(value)

    @field_validator("icon")
    @classmethod
    def check_icon(cls, value: str) -> str:
        return check_icon_ref(value)


class NavItemCreate(BaseModel):
    """Create payload. Icon may be empty; focus pages then receive their default icon."""

    title: str = Field(min_length=1, max_length=50)
    icon: str = Field(default="", max_length=20)
    page_type: str | None = None
    template_id: str | None = None
    group_id: int | None = Field(default=None, ge=1)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return strip_required_text(value)

    @field_validator("icon")
    @classmethod
    # 空图标留给路由补默认值。普通页和模板仍会在路由里要求非空。
    # An empty icon is filled by the route. Blank pages and templates still require one.
    def check_icon(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            return ""
        return check_icon_ref(stripped)

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


class NavItemPatch(BaseModel):
    """Partial nav update. group_id moves the item into another group."""

    title: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = Field(default=None, min_length=1, max_length=20)
    group_id: int | None = Field(default=None, ge=1)

    @field_validator("title", "icon")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return strip_required_text(value)

    @field_validator("icon")
    @classmethod
    def check_icon(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return check_icon_ref(value)


class NavItemRead(NavItemBase):
    id: int
    page_type: str
    group_id: int
    pinned: bool
    locked: bool = False
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
    layer: str = "flex"
    default_icon: str = ""


class TemplateRead(BaseModel):
    id: str
    label: str
    description: str
    icon: str
    page_type: str
    block_count: int


class BookTocItem(BaseModel):
    index: int
    title: str


class BookSummary(BaseModel):
    id: int
    title: str
    author: str
    format: Literal["epub", "txt", "pdf"]
    original_filename: str
    file_size: int
    has_cover: bool
    language: str
    chapter_count: int
    page_count: int
    progress_chapter: int
    progress_offset: float
    progress_ratio: float
    last_read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BookDetail(BookSummary):
    description: str
    toc: list[BookTocItem] = Field(default_factory=list)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=500)
    progress_chapter: int | None = Field(default=None, ge=0)
    progress_offset: float | None = Field(default=None, ge=0, le=1)

    @field_validator("title")
    @classmethod
    # 标题去空白后不能为空；省略表示不改。
    # Strip the title and reject an empty value. None means leave it unchanged.
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped

    @field_validator("author")
    @classmethod
    # 作者允许清空，只去掉首尾空白。
    # Allow clearing the author, and only strip surrounding whitespace.
    def strip_author(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    icon: str = Field(min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return strip_required_text(value)

    @field_validator("icon")
    @classmethod
    def check_icon(cls, value: str) -> str:
        return check_icon_ref(strip_required_text(value))


class GroupCreate(GroupBase):
    description: str = Field(default="", max_length=2000)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "icon")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return strip_required_text(value)

    @field_validator("icon")
    @classmethod
    def check_icon(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return check_icon_ref(value)

    @field_validator("description")
    @classmethod
    # 简介允许清空，只去掉首尾空白。
    # Allow clearing the description, and only strip surrounding whitespace.
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class GroupRead(GroupBase):
    id: int
    description: str
    is_system: bool
    locked: bool = False
    sort_order: int
    item_count: int
    overview_id: int
    created_at: datetime
    updated_at: datetime


class GroupDetail(GroupRead):
    nav_items: list[NavItemRead] = Field(default_factory=list)


class GroupReorder(BaseModel):
    ids: list[int]


class BookContent(BaseModel):
    format: Literal["epub", "txt", "pdf"]
    chapter: int | None
    title: str
    chapter_count: int
    html: str | None = None
    text: str | None = None
    external: bool
    page_count: int
