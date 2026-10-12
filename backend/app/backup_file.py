"""Encrypt and decrypt a Weaveverse backup.

The password is only used to derive a key. It is not stored.
File layout: magic WVBK, version 1, 16-byte salt, 12-byte nonce, AES-GCM ciphertext.

Vault rows travel as plaintext inside that encrypted package. On restore they are
sealed again with the current security password, so an older backup still opens
after the password changes. The security password itself does not travel with the file.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import BACKUPS_DIR, DATA_DIR, DATABASE_PATH
from app.crypto import decrypt_text, derive_key, encrypt_text
from app.privacy import keep_vault_secret, vault_kek_salt, vault_secret
from app.vault_crud import AAD

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
SAFETY_KEEP = 3


def local_stamp(value: datetime | None = None) -> str:
    when = value or datetime.now()
    return when.strftime("%Y-%m-%d %H:%M")


def _add_tree(archive: zipfile.ZipFile, folder: Path, prefix: str) -> None:
    if not folder.is_dir():
        return
    for path in folder.rglob("*"):
        if path.is_file():
            archive.write(path, f"{prefix}/{path.relative_to(folder).as_posix()}")


def _blank_vault_passwords(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "vault_entries" in tables:
            connection.execute("UPDATE vault_entries SET password_encrypted = ''")
            connection.commit()
    finally:
        connection.close()


def build_zip(vault_plain: list[dict]) -> bytes:
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
            _blank_vault_passwords(temp_db)
            archive.write(temp_db, "weaveverse.db")
            temp_db.unlink(missing_ok=True)
        archive.writestr(
            "vault_plain.json",
            json.dumps({"version": 1, "entries": vault_plain}, ensure_ascii=False).encode("utf-8"),
        )
        for name in BACKUP_NAMES:
            path = DATA_DIR / name
            if path.is_file():
                archive.write(path, name)
        for folder in BACKUP_DIRS:
            _add_tree(archive, DATA_DIR / folder, folder)
    return buffer.getvalue()


def encrypt_backup(password: str, vault_plain: list[dict]) -> bytes:
    payload = build_zip(vault_plain)
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


def _read_vault_plain(payload: bytes) -> list[dict] | None:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if "vault_plain.json" not in archive.namelist():
            return None
        data = json.loads(archive.read("vault_plain.json").decode("utf-8"))
    rows = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError("备份里的密码库不完整")
    items = []
    for item in rows:
        if not isinstance(item, dict) or "id" not in item:
            continue
        items.append({"id": int(item["id"]), "password": str(item.get("password") or "")})
    return items


def _legacy_plains(payload: bytes, file_password: str) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        if "weaveverse.db" not in names:
            return []
        raw_db = archive.read("weaveverse.db")
        raw_privacy = archive.read("privacy.json") if "privacy.json" in names else b"{}"
    try:
        meta = json.loads(raw_privacy.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("这份旧备份里的密码库解不开") from exc
    if not isinstance(meta, dict):
        meta = {}
    salt_hex = str(meta.get("security_salt") or meta.get("vault_kek_salt") or "")
    if not salt_hex:
        return []
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError as exc:
        raise ValueError("这份旧备份里的密码库解不开") from exc
    temp = DATA_DIR / "_legacy_vault.db"
    temp.write_bytes(raw_db)
    connection = sqlite3.connect(temp)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "vault_entries" not in tables:
            return []
        rows = connection.execute("SELECT id, password_encrypted FROM vault_entries").fetchall()
    finally:
        connection.close()
        temp.unlink(missing_ok=True)
    items = []
    for entry_id, blob in rows:
        plain = ""
        if blob:
            try:
                plain = decrypt_text(file_password, salt, str(blob), AAD)
            except Exception as exc:
                raise ValueError("这份旧备份里的密码库解不开") from exc
        items.append({"id": int(entry_id), "password": plain})
    return items


def _rewrite_vault(rows: list[dict], current_password: str) -> None:
    salt = vault_kek_salt()
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        for item in rows:
            blob = encrypt_text(current_password, salt, item["password"], AAD)
            connection.execute(
                "UPDATE vault_entries SET password_encrypted = ? WHERE id = ?",
                (blob, int(item["id"])),
            )
        connection.commit()
    finally:
        connection.close()


def _copy_safety_tree(folder: Path, prefix: str) -> None:
    source = DATA_DIR / prefix
    if source.is_dir():
        shutil.copytree(source, folder / prefix, dirs_exist_ok=True)


def _write_safety() -> None:
    SAFETY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    safety = SAFETY_DIR / stamp
    if safety.exists():
        safety = SAFETY_DIR / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    safety.mkdir(parents=True, exist_ok=True)
    if DATABASE_PATH.is_file():
        source = sqlite3.connect(DATABASE_PATH)
        dest = sqlite3.connect(safety / "weaveverse.db")
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()
    for name in BACKUP_NAMES:
        path = DATA_DIR / name
        if path.is_file():
            (safety / name).write_bytes(path.read_bytes())
    for folder in BACKUP_DIRS:
        _copy_safety_tree(safety, folder)
    kept = sorted((path for path in SAFETY_DIR.iterdir() if path.is_dir()), key=lambda path: path.stat().st_mtime, reverse=True)
    for old in kept[SAFETY_KEEP:]:
        shutil.rmtree(old, ignore_errors=True)


def restore_zip(payload: bytes, current_password: str, file_password: str) -> None:
    kept = vault_secret()
    plain = _read_vault_plain(payload)
    if plain is None:
        plain = _legacy_plains(payload, file_password)
    _write_safety()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            destination = _safe_member(info.filename)
            if destination is None or info.is_dir():
                continue
            if Path(info.filename).name == "vault_plain.json":
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(info))
    keep_vault_secret(kept)
    if plain and current_password:
        _rewrite_vault(plain, current_password)


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


def write_backup(password: str, label: str = "", vault_plain: list[dict] | None = None) -> dict:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    blob = encrypt_backup(password, vault_plain or [])
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
    for extra in extras_after(items):
        extra_path = BACKUPS_DIR / extra["filename"]
        if extra_path.is_file() and extra_path != path:
            extra_path.unlink()
    return {
        "filename": filename,
        "path": str(path),
        "label": safe,
        "time": local_stamp(),
        "size": path.stat().st_size,
        "extras": [],
    }


def delete_backup(name: str) -> None:
    path = backup_path(name)
    if not path.is_file():
        raise FileNotFoundError("找不到这个备份")
    path.unlink()
