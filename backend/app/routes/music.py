"""Local audio files for the in-app player. No streaming catalog."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import DATA_DIR
from app.errors import raise_api_error

MUSIC_DIR = DATA_DIR / "music"
INDEX_PATH = MUSIC_DIR / "index.json"
ALLOWED = {".mp3", ".ogg", ".wav", ".m4a", ".flac"}
MAX_BYTES = 40 * 1024 * 1024
LISTS = {"podcast", "liked", "saved", "playlist"}

router = APIRouter(prefix="/music", tags=["music"])


def _load() -> list[dict]:
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    rows = []
    for row in data:
        if not isinstance(row, dict) or not row.get("filename"):
            continue
        item = dict(row)
        if item.get("list") not in LISTS:
            item["list"] = "playlist"
        rows.append(item)
    return rows


def _save(rows: list[dict]) -> None:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("")
def list_tracks() -> dict:
    return {"tracks": _load()}


class TrackList(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    list: str = Field(min_length=1, max_length=20)


@router.post("/list")
def assign_list(data: TrackList) -> dict:
    if data.list not in LISTS:
        raise_api_error(400, "list", "没有这个歌单")
    name = Path(data.filename).name
    rows = _load()
    found = None
    for row in rows:
        if row.get("filename") == name:
            row["list"] = data.list
            found = row
    if found is None:
        raise_api_error(404, "filename", "音频不存在")
    _save(rows)
    return found


@router.post("")
async def upload_track(file: UploadFile, list_name: str = Form(default="playlist", alias="list")) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise_api_error(400, "file", "只支持 mp3 / ogg / wav / m4a / flac")
    payload = await file.read()
    if not payload:
        raise_api_error(400, "file", "空文件")
    if len(payload) > MAX_BYTES:
        raise_api_error(400, "file", "音频超过 40MB")
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    (MUSIC_DIR / filename).write_bytes(payload)
    title = Path(file.filename or filename).stem[:80] or "未命名"
    rows = _load()
    track = {"filename": filename, "title": title, "list": list_name if list_name in LISTS else "playlist"}
    rows.append(track)
    _save(rows)
    return track


@router.delete("/{filename}")
def delete_track(filename: str) -> dict:
    name = Path(filename).name
    if name != filename:
        raise_api_error(400, "filename", "非法文件名")
    rows = [row for row in _load() if row.get("filename") != name]
    _save(rows)
    path = MUSIC_DIR / name
    if path.is_file():
        path.unlink()
    return {"status": "ok"}


@router.get("/files/{filename}")
def read_track(filename: str):
    name = Path(filename).name
    path = MUSIC_DIR / name
    if name != filename or not path.is_file():
        raise_api_error(404, "filename", "音频不存在")
    return FileResponse(path)
