"""Top-level API router aggregation for Weaveverse OS."""

from __future__ import annotations

from fastapi import APIRouter

from app.routes.nav import router as nav_router

router = APIRouter(prefix="/api")


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(nav_router)
