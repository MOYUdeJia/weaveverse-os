"""Store private-album passwords in Windows Credential Manager.

The photos themselves stay plain files. This module only checks a password
before the API returns a private album. If Credential Manager is unavailable,
a PBKDF2 hash is written to backend/data/album_secrets.json.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
from ctypes import wintypes

from app.config import DATA_DIR

SERVICE = "weaveverse-os"
_SECRETS_PATH = DATA_DIR / "album_secrets.json"
_PBKDF2_ROUNDS = 200_000


def _target(album_id: int) -> str:
    return f"{SERVICE}/album/{album_id}"


def _credential_blob(secret: str) -> bytes:
    return secret.encode("utf-8")


class _FileTime(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", _FileTime),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def vault_write(target: str, secret: str, username: str) -> None:
    blob = _credential_blob(secret)
    buffer = ctypes.create_string_buffer(blob)
    cred = _Credential()
    cred.Type = 1
    cred.TargetName = target
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))
    cred.Persist = 2
    cred.UserName = username
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
    advapi.CredWriteW.restype = wintypes.BOOL
    if not advapi.CredWriteW(ctypes.byref(cred), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def vault_read(target: str) -> str | None:
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_Credential)),
    ]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    pointer = ctypes.POINTER(_Credential)()
    if not advapi.CredReadW(target, 1, 0, ctypes.byref(pointer)):
        error = ctypes.get_last_error()
        if error == 1168:
            return None
        raise ctypes.WinError(error)
    try:
        raw = ctypes.string_at(pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize)
        return raw.decode("utf-8")
    finally:
        advapi.CredFree(pointer)


def vault_delete(target: str) -> None:
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    advapi.CredDeleteW.restype = wintypes.BOOL
    advapi.CredDeleteW(target, 1, 0)


def _vault_write(album_id: int, password: str) -> None:
    vault_write(_target(album_id), password, "album")


def _vault_read(album_id: int) -> str | None:
    return vault_read(_target(album_id))


def _vault_delete(album_id: int) -> None:
    vault_delete(_target(album_id))


def _load_hashes() -> dict:
    try:
        data = json.loads(_SECRETS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_hashes(data: dict) -> None:
    _SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SECRETS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_write(album_id: int, password: str) -> None:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    data = _load_hashes()
    data[str(album_id)] = {"salt": salt.hex(), "hash": digest.hex()}
    _save_hashes(data)


def _hash_check(album_id: int, password: str) -> bool:
    row = _load_hashes().get(str(album_id))
    if not isinstance(row, dict):
        return False
    try:
        salt = bytes.fromhex(str(row.get("salt") or ""))
        expected = str(row.get("hash") or "")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return digest.hex() == expected


def _hash_clear(album_id: int) -> None:
    data = _load_hashes()
    if str(album_id) in data:
        data.pop(str(album_id), None)
        _save_hashes(data)


def set_album_password(album_id: int, password: str) -> str:
    if os.name == "nt":
        try:
            _vault_write(album_id, password)
            _hash_clear(album_id)
            return "keyring"
        except OSError:
            pass
    _hash_write(album_id, password)
    return "hash"


def check_album_password(album_id: int, password: str) -> bool:
    if os.name == "nt":
        try:
            stored = _vault_read(album_id)
        except OSError:
            stored = None
        if stored is not None:
            return stored == password
    return _hash_check(album_id, password)


def clear_album_password(album_id: int) -> None:
    if os.name == "nt":
        try:
            _vault_delete(album_id)
        except OSError:
            pass
    _hash_clear(album_id)
