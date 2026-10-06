"""FastAPI app factory and production SPA static-file fallback."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import FRONTEND_DIST, is_dev_mode


def create_app() -> FastAPI:
    app = FastAPI(title="Weaveverse OS")
    register_error_handlers(app)
    app.include_router(api_router)

    if not is_dev_mode():
        mount_frontend(app)

    return app


def register_error_handlers(app: FastAPI) -> None:
    """Keep API validation errors in the M1 response shape."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": "请求参数错误"})


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
