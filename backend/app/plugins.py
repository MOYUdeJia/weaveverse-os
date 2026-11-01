"""Installed plugins live in data/plugins/<id>/manifest.json.

The host serves each plugin's files into a sandboxed iframe. Plugins do not
share the app origin, and their pages cannot call the HTTP API.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import zipfile
from pathlib import Path

from app.config import DATA_DIR

PLUGINS_DIR = DATA_DIR / "plugins"
BUNDLED_DIR = Path(__file__).resolve().parent / "bundled_plugins"
MAX_ZIP = 8 * 1024 * 1024
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
_ENTRY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,80}$")


def ensure_seed() -> None:
    """Copy the bundled Hello World the first time the folder is used."""
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    marker = PLUGINS_DIR / ".seeded"
    if marker.exists():
        return
    source = BUNDLED_DIR / "hello-world"
    dest = PLUGINS_DIR / "hello-world"
    if source.is_dir() and not dest.exists():
        shutil.copytree(source, dest)
    marker.write_text("hello-world\n", encoding="utf-8")


def list_plugins() -> list[dict]:
    ensure_seed()
    found = []
    for folder in sorted(PLUGINS_DIR.iterdir(), key=lambda path: path.name):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        item = read_manifest(folder)
        if item is not None:
            found.append(item)
    return found


def read_manifest(folder: Path) -> dict | None:
    path = folder / "manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(data, dict):
        return None
    plugin_id = str(data.get("id") or "")
    entry = str(data.get("entry") or "")
    if not _ID.fullmatch(plugin_id) or plugin_id != folder.name or not _ENTRY.fullmatch(entry):
        return None
    if not (folder / entry).is_file():
        return None
    name = str(data.get("name") or plugin_id)[:40]
    version = str(data.get("version") or "0")[:20]
    icon = str(data.get("icon") or name[:1])[:4]
    return {
        "id": plugin_id,
        "name": name,
        "version": version,
        "icon": icon,
        "entry": entry,
    }


def plugin_file(plugin_id: str, relative: str) -> Path:
    folder = _folder(plugin_id)
    rel = relative.replace("\\", "/").lstrip("/")
    if not rel or any(part in {"", ".", ".."} for part in rel.split("/")):
        raise ValueError("文件不存在")
    path = (folder / rel).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():
        raise ValueError("文件不存在")
    return path


def install_zip(payload: bytes) -> dict:
    ensure_seed()
    if len(payload) > MAX_ZIP:
        raise ValueError("压缩包超过 8MB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("这不是一个 zip") from exc
    with archive:
        names = [info.filename.replace("\\", "/") for info in archive.infolist() if info.filename]
        root = _common_root(names)
        manifest_name = f"{root}manifest.json"
        try:
            raw = archive.read(manifest_name)
        except KeyError as exc:
            raise ValueError("压缩包里没有 manifest.json") from exc
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("manifest.json 读不出来") from exc
        plugin_id = str(data.get("id") or "")
        entry = str(data.get("entry") or "")
        if not _ID.fullmatch(plugin_id) or not _ENTRY.fullmatch(entry):
            raise ValueError("manifest.json 的 id 或 entry 不合规")
        staging_root = PLUGINS_DIR / ".staging"
        if staging_root.exists():
            shutil.rmtree(staging_root)
        folder = staging_root / plugin_id
        folder.mkdir(parents=True)
        try:
            _extract(archive, folder, root)
            item = read_manifest(folder)
            if item is None or item["id"] != plugin_id:
                raise ValueError("manifest.json 和目录对不上")
        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise
        dest = PLUGINS_DIR / plugin_id
        if dest.exists():
            shutil.rmtree(dest)
        folder.rename(dest)
        shutil.rmtree(staging_root, ignore_errors=True)
        return item


def export_zip(plugin_id: str) -> bytes:
    folder = _folder(plugin_id)
    if read_manifest(folder) is None:
        raise ValueError("没有这个插件")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in folder.rglob("*"):
            if path.is_file() and not any(part.startswith(".") for part in path.relative_to(folder).parts):
                archive.write(path, f"{plugin_id}/{path.relative_to(folder).as_posix()}")
    return buffer.getvalue()


def delete_plugin(plugin_id: str) -> None:
    folder = _folder(plugin_id)
    if read_manifest(folder) is None:
        raise ValueError("没有这个插件")
    shutil.rmtree(folder)


def _folder(plugin_id: str) -> Path:
    if not _ID.fullmatch(plugin_id):
        raise ValueError("没有这个插件")
    folder = (PLUGINS_DIR / plugin_id).resolve()
    if not folder.is_relative_to(PLUGINS_DIR.resolve()) or not folder.is_dir():
        raise ValueError("没有这个插件")
    return folder


def _common_root(names: list[str]) -> str:
    files = [name for name in names if not name.endswith("/")]
    if not files:
        raise ValueError("压缩包是空的")
    first = files[0].split("/", 1)[0]
    if all(name == first or name.startswith(first + "/") for name in files):
        if any(name.startswith(first + "/") for name in files):
            return first + "/"
    return ""


def _extract(archive: zipfile.ZipFile, staging: Path, root: str) -> None:
    base = staging.resolve()
    written = 0
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        if not name or name.endswith("/"):
            continue
        if root:
            if not name.startswith(root):
                continue
            rel = name[len(root) :]
        else:
            rel = name
        if not rel or any(part in {"", ".", ".."} for part in rel.split("/")):
            raise ValueError("压缩包路径不安全")
        target = (staging / rel).resolve()
        if not target.is_relative_to(base):
            raise ValueError("压缩包路径不安全")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, target.open("wb") as out:
            shutil.copyfileobj(src, out)
        written += target.stat().st_size
        if written > MAX_ZIP * 4:
            raise ValueError("解压后的插件太大")
