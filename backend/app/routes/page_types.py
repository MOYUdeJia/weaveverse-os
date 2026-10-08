"""HTTP route for the page type registry."""

from __future__ import annotations

from fastapi import APIRouter

from app.page_types import PAGE_TYPES
from app.schemas import PageTypeRead


router = APIRouter(prefix="/page-types", tags=["page-types"])


@router.get("", response_model=list[PageTypeRead])
# 返回已注册的全部页面类型元数据。
# Return metadata for every registered page type.
def get_page_types() -> list[dict]:
    return [
        {
            "type": key,
            "label": spec["label"],
            "multi_instance": spec["multi_instance"],
            "layer": spec.get("layer") or "flex",
            "default_icon": spec.get("default_icon") or "",
        }
        for key, spec in PAGE_TYPES.items()
    ]
