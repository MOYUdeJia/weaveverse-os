"""Store AI API keys in Windows Credential Manager.

Target name is weaveverse-os/ai/{provider}. The key is never written to the
database. If Credential Manager fails, it falls back to ai_secrets.json.
"""

from __future__ import annotations

import json
import os

from app.album_lock import vault_delete, vault_read, vault_write
from app.config import DATA_DIR

_PATH = DATA_DIR / "ai_secrets.json"


def _target(provider: str) -> str:
    return f"weaveverse-os/ai/{provider}"


def _load() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data), encoding="utf-8")


def _file_clear(provider: str) -> None:
    data = _load()
    if provider in data:
        data.pop(provider, None)
        _save(data)


def set_api_key(provider: str, api_key: str) -> str:
    if os.name == "nt":
        try:
            vault_write(_target(provider), api_key, "ai")
            _file_clear(provider)
            return "keyring"
        except OSError:
            pass
    data = _load()
    data[provider] = api_key
    _save(data)
    return "file"


def get_api_key(provider: str) -> str | None:
    if os.name == "nt":
        try:
            stored = vault_read(_target(provider))
        except OSError:
            stored = None
        if stored:
            return stored
    value = _load().get(provider)
    if isinstance(value, str) and value:
        return value
    return None


def has_api_key(provider: str) -> bool:
    return bool(get_api_key(provider))


def clear_api_key(provider: str) -> None:
    if os.name == "nt":
        try:
            vault_delete(_target(provider))
        except OSError:
            pass
    _file_clear(provider)
