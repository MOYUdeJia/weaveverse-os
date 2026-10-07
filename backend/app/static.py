"""FastAPI app factory and production SPA static-file fallback."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import FRONTEND_DIST, is_dev_mode
from app.errors import detail_from_validation_error


# 创建 FastAPI 应用并挂上 API 与静态资源。
# Create the FastAPI app and attach the API plus static files.
def create_app() -> FastAPI:
    app = FastAPI(title="Weaveverse OS")
    register_error_handlers(app)
    app.include_router(api_router)

    if not is_dev_mode():
        mount_frontend(app)

    return app


# 把校验错误和 HTTP 错误统一成 {field, message}。
# Normalize validation and HTTP errors into {field, message}.
def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": detail_from_validation_error(exc)})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, str):
            detail = {"field": "detail", "message": detail}
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})


# 生产模式托管 frontend/dist，非 API 路径回退到 index.html。
# Serve frontend/dist in production and fall back to index.html for non-API paths.
def mount_frontend(app: FastAPI) -> None:
    assets_dir = FRONTEND_DIST / "assets"
    index_file = FRONTEND_DIST / "index.html"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail={"field": "path", "message": "接口不存在"})
        if not index_file.exists():
            raise HTTPException(
                status_code=503,
                detail={"field": "frontend", "message": "frontend/dist 不存在，请先在 frontend 执行 npm run build。"},
            )
        return FileResponse(index_file)
