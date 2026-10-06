"""Request and response schemas for API boundaries."""
#只管理数据库连接，数据校验
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class NavItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    icon: str = Field(min_length=1, max_length=8)

    @field_validator("title", "icon")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class NavItemCreate(NavItemBase):
    pass


class NavItemUpdate(NavItemBase):
    pass


class NavItemRead(NavItemBase):
    id: int
    sort_order: int
    created_at: datetime
    updated_at: datetime
