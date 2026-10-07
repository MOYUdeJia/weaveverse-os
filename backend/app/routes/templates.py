"""HTTP route for the built-in page templates."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import TemplateRead
from app.templates import list_template_summaries


router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateRead])
# 返回模板元信息，不含 default_blocks。
# Return template metadata without the preset blocks.
def get_templates() -> list[dict]:
    return list_template_summaries()
