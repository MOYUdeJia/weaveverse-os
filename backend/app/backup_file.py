"""Encrypt and decrypt a Weaveverse backup.

The password is only used to derive a key. It is not stored.
File layout: magic WVBK, version 1, 16-byte salt, 12-byte nonce, AES-GCM ciphertext.
"""

from __future__ import annotations

import io
import os
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import DATA_DIR, DATABASE_PATH

MAGIC = b"WVBK"
VERSION = 1
BACKUP_NAMES = (
    "appearance.json",
    "quick_tags.json",
    "ai_settings.json",
)
BACKUP_DIRS = ("attachments", "books", "music", "icons", "backgrounds")
SAFETY_DIR = DATA_DIR / "safety"
META_PATH = DATA_DIR / "backup_meta.json"


def _derive(password: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        password.encode("utf-8"),
        salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID,
    )


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
    key = _derive(password, salt)
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
    key = _derive(password, salt)
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


def remember_backup() -> None:
    import json

    META_PATH.write_text(
        json.dumps({"last_backup_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )


def last_backup_at() -> str:
    import json

    try:
        data = json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(data.get("last_backup_at") or "") if isinstance(data, dict) else ""
