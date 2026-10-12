"""One security password for the vault and for backups.

The Argon2id hash and the key-derivation salt live in privacy.json.
Plaintext stays in process memory for this session only.
Opening the vault and opening backup are separate unlocks, but they check the same secret.
"""

from __future__ import annotations

import json
import os
from typing import Literal

from app.config import DATA_DIR
from app.crypto import hash_password, verify_password

Kind = Literal["vault", "backup"]

PRIVACY_PATH = DATA_DIR / "privacy.json"
MIN_PASSWORD = 8
MAX_PASSWORD = 200

_session: dict[str, str | None] = {"vault": None, "backup": None}


def _load() -> dict:
    try:
        data = json.loads(PRIVACY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    legacy = any(key in data for key in ("backup_hash", "vault_hash", "vault_kek_salt"))
    if data.get("vault_hash") and not data.get("security_hash"):
        data["security_hash"] = data["vault_hash"]
    if data.get("vault_kek_salt") and not data.get("security_salt"):
        data["security_salt"] = data["vault_kek_salt"]
    if legacy:
        data.pop("backup_hash", None)
        data.pop("vault_hash", None)
        data.pop("vault_kek_salt", None)
        _save(data)
    return data


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


def _hash(data: dict) -> str:
    return str(data.get("security_hash") or "")


def _salt(data: dict) -> str:
    return str(data.get("security_salt") or "")


def security_material() -> tuple[str, str] | None:
    data = _load()
    stored = _hash(data)
    salt = _salt(data)
    if not stored or not salt:
        return None
    return stored, salt


def security_secret() -> dict | None:
    found = security_material()
    if found is None:
        return None
    stored, salt = found
    return {"security_hash": stored, "security_salt": salt}


def vault_secret() -> dict | None:
    return security_secret()


def keep_security_secret(saved: dict | None) -> None:
    if not saved:
        return
    data = _load()
    data["security_hash"] = saved["security_hash"]
    data["security_salt"] = saved["security_salt"]
    data.pop("vault_hash", None)
    data.pop("vault_kek_salt", None)
    data.pop("backup_hash", None)
    _save(data)


def keep_vault_secret(saved: dict | None) -> None:
    keep_security_secret(saved)


def security_hint() -> str:
    data = _load()
    return str(data.get("security_hint") or "").strip()[:80]


def status() -> dict:
    ready = security_material() is not None
    return {
        "security_set": ready,
        "security_hint": security_hint(),
        "vault_set": ready,
        "vault_unlocked": _session["vault"] is not None,
        "backup_set": ready,
        "backup_unlocked": _session["backup"] is not None,
    }


def vault_kek_salt() -> bytes:
    found = security_material()
    if found is None:
        raise RuntimeError("还没有设置安全密码")
    return bytes.fromhex(found[1])


def session_password(kind: Kind) -> str | None:
    return _session[kind]


def remember(kind: Kind, password: str) -> None:
    _session[kind] = password


def snapshot_file() -> dict:
    return dict(_load())


def restore_file(data: dict) -> None:
    _save(data)


def write_security(password: str, salt: bytes, hint: str | None = None) -> None:
    data = _load()
    data["security_hash"] = hash_password(password)
    data["security_salt"] = salt.hex()
    data.pop("vault_hash", None)
    data.pop("vault_kek_salt", None)
    data.pop("backup_hash", None)
    if hint is not None:
        cleaned = " ".join(hint.split())[:80]
        if cleaned:
            data["security_hint"] = cleaned
        else:
            data.pop("security_hint", None)
    _save(data)


def clear_security() -> None:
    data = _load()
    for key in ("security_hash", "security_salt", "security_hint", "backup_hash", "vault_hash", "vault_kek_salt"):
        data.pop(key, None)
    _save(data)
    lock()


def require_session(kind: Kind) -> str:
    password = _session[kind]
    if password:
        return password
    if security_material() is None:
        raise PermissionError("请先设置安全密码")
    raise PermissionError("请先输入安全密码")


def lock(kind: Kind | None = None) -> None:
    if kind is None:
        _session["vault"] = None
        _session["backup"] = None
        return
    _session[kind] = None


def unlock(kind: Kind, password: str) -> None:
    found = security_material()
    if found is None:
        raise PermissionError("还没有设置安全密码")
    text = password.strip()
    if not verify_password(found[0], text):
        raise PermissionError("密码不对")
    _session[kind] = text
