"""Argon2id key derivation and AES-GCM helpers.

Passwords are only used in memory. This module never writes them to disk.
"""

from __future__ import annotations

import os

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32)


def derive_key(password: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        password.encode("utf-8"),
        salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID,
    )


def hash_password(password: str) -> str:
    return HASHER.hash(password)


def verify_password(stored: str, password: str) -> bool:
    if not stored:
        return False
    try:
        return HASHER.verify(stored, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def encrypt_bytes(key: bytes, payload: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, payload, aad)


def decrypt_bytes(key: bytes, blob: bytes, aad: bytes) -> bytes:
    if len(blob) < 12 + 16:
        raise ValueError("密文不完整")
    return AESGCM(key).decrypt(blob[:12], blob[12:], aad)


def encrypt_text(password: str, salt: bytes, text: str, aad: bytes) -> str:
    key = derive_key(password, salt)
    try:
        return encrypt_bytes(key, text.encode("utf-8"), aad).hex()
    finally:
        del key


def decrypt_text(password: str, salt: bytes, stored: str, aad: bytes) -> str:
    key = derive_key(password, salt)
    try:
        return decrypt_bytes(key, bytes.fromhex(stored), aad).decode("utf-8")
    finally:
        del key
