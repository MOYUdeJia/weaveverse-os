"""Encrypt and decrypt a Weaveverse backup.

The password is only used to derive a key. It is not stored.
File layout: magic WVBK, version 1, 16-byte salt, 12-byte nonce, AES-GCM ciphertext.
"""

from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import BACKUPS_DIR, DATA_DIR, DATABASE_PATH
from app.crypto import derive_key
from app.privacy import keep_vault_secret, vault_secret

MAGIC = b"WVBK"
VERSION = 1
BACKUP_NAMES = (
    "appearance.json",
    "quick_tags.json",
    "ai_settings.json",
    "privacy.json",
)
BACKUP_DIRS = ("attachments", "books", "music", "icons", "backgrounds")
SAFETY_DIR = DATA_DIR / "safety"
META_PATH = DATA_DIR / "backup_meta.json"
NAME_PATTERN = re.compile(r"^weaveverse-(\d{4}-\d{2}-\d{2})-(\d{4})(?:-(.+))?\.wvbak$")
KEEP = 5


def local_stamp(value: datetime | None = None) -> str:
    when = value or datetime.now()
    return when.strftime("%Y-%m-%d %H:%M")


def _add_tree(archive: zipfile.ZipFile, folder: Path, prefix: str) -> None:
    if not folder.is_dir():
        return
    for path in folder.rglob("*"):
        if path.is_file():
            archive.write(path, f"{prefix}/{path.relative_to(folder).as_posix()}")


def build_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        temp_db = DATA_DIR / "_backup_snapshot.db"
        if DATABASE_PATH.is_file():
            source = sqlite3.connect(DATABASE_PATH)
            target = sqlite3.connect(temp_db)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            archive.write(temp_db, "weaveverse.db")
            temp_db.unlink(missing_ok=True)
        for name in BACKUP_NAMES:
            path = DATA_DIR / name
            if path.is_file():
                archive.write(path, name)
        for folder in BACKUP_DIRS:
            _add_tree(archive, DATA_DIR / folder, folder)
    return buffer.getvalue()


def encrypt_backup(password: str) -> bytes:
    payload = build_zip()
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = derive_key(password, salt)
    try:
        ciphertext = AESGCM(key).encrypt(nonce, payload, MAGIC)
    finally:
        del key
    return MAGIC + bytes([VERSION]) + salt + nonce + ciphertext


def decrypt_backup(blob: bytes, password: str) -> bytes:
    if len(blob) < 4 + 1 + 16 + 12 + 16 or blob[:4] != MAGIC or blob[4] != VERSION:
        raise ValueError("这不是 Weaveverse 备份")
    salt = blob[5:21]
    nonce = blob[21:33]
    ciphertext = blob[33:]
    key = derive_key(password, salt)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, MAGIC)
    except Exception as exc:
        raise ValueError("密码不对") from exc
    finally:
        del key


def _safe_member(name: str) -> Path | None:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        return None
    return DATA_DIR / path


def restore_zip(payload: bytes) -> None:
    kept = vault_secret()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safety = SAFETY_DIR / stamp
    safety.mkdir(parents=True, exist_ok=True)
    if DATABASE_PATH.is_file():
        target = safety / "weaveverse.db"
        source = sqlite3.connect(DATABASE_PATH)
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()
    for name in BACKUP_NAMES:
        path = DATA_DIR / name
        if path.is_file():
            (safety / name).write_bytes(path.read_bytes())
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            destination = _safe_member(info.filename)
            if destination is None or info.is_dir():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(info))
    keep_vault_secret(kept)


def remember_backup() -> None:
    META_PATH.write_text(
        json.dumps({"last_backup_at": datetime.now().strftime("%Y-%m-%d %H:%M")}),
        encoding="utf-8",
    )


def last_backup_at() -> str:
    try:
        data = json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    raw = str(data.get("last_backup_at") or "") if isinstance(data, dict) else ""
    if "T" in raw:
        raw = raw.replace("T", " ")[:16]
    return raw[:16]


def sanitize_label(label: str) -> str:
    text = re.sub(r'[<>:"/\\|?*]+', "", label).strip().replace(" ", "-")
    return text[:40]


def backup_path(name: str) -> Path:
    filename = Path(name).name
    if filename != name or not NAME_PATTERN.fullmatch(filename):
        raise ValueError("备份文件名不合法")
    return BACKUPS_DIR / filename


def list_backups() -> list[dict]:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for path in BACKUPS_DIR.iterdir():
        if not path.is_file():
            continue
        match = NAME_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        hour = match.group(2)
        label = match.group(3) or ""
        items.append(
            {
                "filename": path.name,
                "label": label,
                "time": f"{match.group(1)} {hour[:2]}:{hour[2:]}",
                "size": path.stat().st_size,
                "mtime": path.stat().st_mtime,
            }
        )
    items.sort(key=lambda item: item["mtime"], reverse=True)
    for item in items:
        item.pop("mtime", None)
    return items


def extras_after(items: list[dict]) -> list[dict]:
    return items[KEEP:]


def write_backup(password: str, label: str = "") -> dict:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    blob = encrypt_backup(password)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    safe = sanitize_label(label)
    filename = f"weaveverse-{stamp}-{safe}.wvbak" if safe else f"weaveverse-{stamp}.wvbak"
    path = BACKUPS_DIR / filename
    if path.exists():
        filename = f"weaveverse-{stamp}-{safe + '-' if safe else ''}{os.urandom(2).hex()}.wvbak"
        path = BACKUPS_DIR / filename
    path.write_bytes(blob)
    remember_backup()
    items = list_backups()
    return {
        "filename": filename,
        "path": str(path),
        "label": safe,
        "time": local_stamp(),
        "size": path.stat().st_size,
        "extras": extras_after(items),
    }


def delete_backup(name: str) -> None:
    path = backup_path(name)
    if not path.is_file():
        raise FileNotFoundError("找不到这个备份")
    path.unlink()
