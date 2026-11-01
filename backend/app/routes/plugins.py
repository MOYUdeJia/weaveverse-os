"""List, serve, import, export and delete plugins under data/plugins."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse, Response

from app.config import PROJECT_ROOT
from app.errors import raise_api_error
from app.plugins import delete_plugin, export_zip, install_zip, list_plugins, plugin_file

router = APIRouter(prefix="/plugins", tags=["plugins"])

_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
}

# The iframe is a unique origin. This policy blocks network calls from the page.
_CSP = (
    "default-src 'none'; "
    "script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; "
    "img-src data:; "
    "connect-src 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'self'; "
    "base-uri 'none'"
)


@router.get("")
def get_plugins() -> dict:
    return {"items": list_plugins()}


@router.get("/guide")
def get_plugin_guide() -> dict:
    path = PROJECT_ROOT / "docs" / "PLUGIN-GUIDE.md"
    if not path.is_file():
        raise_api_error(404, "file", "开发者文档不在")
    return {"markdown": path.read_text(encoding="utf-8")}


@router.post("/import")
async def import_plugin(file: UploadFile = File(...)) -> dict:
    payload = await file.read()
    try:
        item = install_zip(payload)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))
    return item


@router.get("/{plugin_id}/export")
def download_plugin(plugin_id: str) -> Response:
    try:
        body = export_zip(plugin_id)
    except ValueError as exc:
        raise_api_error(404, "id", str(exc))
    return Response(
        content=body,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{plugin_id}.zip"'},
    )


@router.delete("/{plugin_id}")
def remove_plugin(plugin_id: str) -> dict:
    try:
        delete_plugin(plugin_id)
    except ValueError as exc:
        raise_api_error(404, "id", str(exc))
    return {"deleted": plugin_id}


@router.get("/{plugin_id}/files/{file_path:path}")
def read_plugin_file(plugin_id: str, file_path: str) -> FileResponse:
    try:
        path = plugin_file(plugin_id, file_path)
    except ValueError as exc:
        raise_api_error(404, "file", str(exc))
    media = _TYPES.get(path.suffix.lower(), "application/octet-stream")
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if path.suffix.lower() == ".html":
        headers["Content-Security-Policy"] = _CSP
    return FileResponse(path, media_type=media, headers=headers)
