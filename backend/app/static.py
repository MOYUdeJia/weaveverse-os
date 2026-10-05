"""FastAPI app factory and production SPA static-file fallback."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import FRONTEND_DIST, is_dev_mode


def create_app() -> FastAPI:
    app = FastAPI(title="Weaveverse OS")
    app.include_router(api_router)

    if not is_dev_mode():
        mount_frontend(app)

    return app


def mount_frontend(app: FastAPI) -> None:
    """Serve Vite's production build and fall back to index.html for SPA paths."""
    assets_dir = FRONTEND_DIST / "assets"
    index_file = FRONTEND_DIST / "index.html"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        if not index_file.exists():
            raise HTTPException(
                status_code=503,
                detail="frontend/dist is missing. Run npm run build in frontend first.",
            )
        return FileResponse(index_file)
