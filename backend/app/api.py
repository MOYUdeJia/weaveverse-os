"""Top-level API router aggregation for Weaveverse OS."""

from __future__ import annotations

from fastapi import APIRouter

from app.errors import raise_api_error
from app.routes.blocks import router as blocks_router
from app.routes.books import router as books_router
from app.routes.nav import router as nav_router
from app.routes.page_types import router as page_types_router
from app.routes.templates import router as templates_router


router = APIRouter(prefix="/api")


@router.get("/health")
# 健康检查，供前端确认后端已就绪。
# Health check so the frontend can confirm the backend is ready.
def get_health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(page_types_router)
router.include_router(templates_router)
router.include_router(nav_router)
router.include_router(blocks_router)
router.include_router(books_router)


@router.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
# 未匹配的 /api 路径返回 JSON 404，避免落到 SPA。
# Unknown /api paths return JSON 404 instead of the SPA fallback.
def api_not_found(full_path: str):
    raise_api_error(404, "path", "接口不存在")
