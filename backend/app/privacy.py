"""Privacy passwords for the vault and for backups.

Stores Argon2 hashes and a vault key-derivation salt in privacy.json.
Plaintext passwords stay in process memory for the current session only.
"""

from __future__ import annotations

import json
import os
from typing import Literal

from app.config import DATA_DIR
from app.crypto import hash_password, verify_password

Kind = Literal["vault", "backup"]

PRIVACY_PATH = DATA_DIR / "privacy.json"
MIN_PASSWORD = 12
MAX_PASSWORD = 200

_session: dict[str, str | None] = {"vault": None, "backup": None}


def _load() -> dict:
    try:
        data = json.loads(PRIVACY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRIVACY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def check_length(password: str) -> str:
    text = password.strip()
    if len(text) < MIN_PASSWORD:
        raise ValueError(f"密码至少 {MIN_PASSWORD} 位")
    if len(text) > MAX_PASSWORD:
        raise ValueError("密码太长")
    return text


def status() -> dict:
    data = _load()
    return {
        "vault_set": bool(data.get("vault_hash")),
        "vault_unlocked": _session["vault"] is not None,
        "backup_set": bool(data.get("backup_hash")),
        "backup_unlocked": _session["backup"] is not None,
    }


def vault_kek_salt() -> bytes:
    data = _load()
    raw = str(data.get("vault_kek_salt") or "")
    if not raw:
        raise RuntimeError("还没有设置主密码")
    return bytes.fromhex(raw)


def session_password(kind: Kind) -> str | None:
    return _session[kind]


def remember(kind: Kind, password: str) -> None:
    _session[kind] = password


def snapshot_file() -> dict:
    return dict(_load())


def restore_file(data: dict) -> None:
    _save(data)


def require_session(kind: Kind) -> str:
    password = _session[kind]
    if password:
        return password
    label = "主密码" if kind == "vault" else "备份密码"
    if not status()[f"{kind}_set"]:
        raise PermissionError(f"请先设置{label}")
    raise PermissionError(f"请先输入{label}")


def lock(kind: Kind | None = None) -> None:
    if kind is None:
        _session["vault"] = None
        _session["backup"] = None
        return
    _session[kind] = None


def unlock(kind: Kind, password: str) -> None:
    data = _load()
    stored = str(data.get(f"{kind}_hash") or "")
    if not stored:
        raise PermissionError("还没有设置密码")
    text = password.strip()
    if not verify_password(stored, text):
        raise PermissionError("密码不对")
    _session[kind] = text


def set_password(kind: Kind, password: str, current: str = "") -> None:
    text = check_length(password)
    data = _load()
    stored = str(data.get(f"{kind}_hash") or "")
    if stored:
        if not current:
            raise PermissionError("请输入当前密码")
        if not verify_password(stored, current):
            raise PermissionError("当前密码不对")
    data[f"{kind}_hash"] = hash_password(text)
    if kind == "vault":
        data["vault_kek_salt"] = os.urandom(16).hex()
    _save(data)
    _session[kind] = text
