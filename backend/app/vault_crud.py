"""Password-vault sections and entries.

Entry passwords are encrypted with the session security password.
Changing that password re-encrypts every row in one database transaction,
then writes the new hash. If the file write fails, the old ciphertext is put back.
"""

from __future__ import annotations

import os

from sqlmodel import Session, col, select

from app.crypto import decrypt_bytes, decrypt_text, derive_key, encrypt_bytes, encrypt_text, verify_password
from app.models import VaultEntry, VaultSection, utc_now
from app.privacy import require_session, vault_kek_salt

AAD = b"WVLT"


def _encrypt(text: str) -> str:
    return encrypt_text(require_session("vault"), vault_kek_salt(), text, AAD)


def _decrypt(stored: str) -> str:
    if not stored:
        return ""
    return decrypt_text(require_session("vault"), vault_kek_salt(), stored, AAD)


def section_to_dict(row: VaultSection) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "sort_order": row.sort_order,
        "created_at": row.created_at,
    }


def entry_to_dict(row: VaultEntry) -> dict:
    return {
        "id": row.id,
        "section_id": row.section_id,
        "name": row.name,
        "url": row.url,
        "username": row.username,
        "password": _decrypt(row.password_encrypted),
        "note": row.note,
        "sort_order": row.sort_order,
        "pinned": row.pinned,
        "locked": row.locked,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_sections(session: Session) -> list[VaultSection]:
    statement = select(VaultSection).order_by(col(VaultSection.sort_order), col(VaultSection.id))
    return list(session.exec(statement).all())


def get_section(session: Session, section_id: int) -> VaultSection | None:
    return session.get(VaultSection, section_id)


def create_section(session: Session, name: str) -> VaultSection:
    max_order = session.exec(select(col(VaultSection.sort_order)).order_by(col(VaultSection.sort_order).desc())).first()
    row = VaultSection(
        name=name,
        sort_order=0 if max_order is None else int(max_order) + 1,
        created_at=utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def rename_section(session: Session, row: VaultSection, name: str) -> VaultSection:
    row.name = name
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_section(session: Session, row: VaultSection) -> None:
    entries = session.exec(select(VaultEntry).where(VaultEntry.section_id == row.id)).all()
    for entry in entries:
        session.delete(entry)
    session.delete(row)
    session.commit()


def reorder_sections(session: Session, ids: list[int]) -> list[VaultSection]:
    rows = {row.id: row for row in list_sections(session)}
    for index, section_id in enumerate(ids):
        row = rows.get(section_id)
        if row is None:
            continue
        row.sort_order = index
        session.add(row)
    session.commit()
    return list_sections(session)


def count_entries(session: Session) -> int:
    return len(session.exec(select(VaultEntry.id)).all())


def wipe_vault(session: Session) -> int:
    rows = list(session.exec(select(VaultEntry)).all())
    sections = list(session.exec(select(VaultSection)).all())
    for row in rows:
        session.delete(row)
    for row in sections:
        session.delete(row)
    session.commit()
    return len(rows)


def list_entries(session: Session) -> list[VaultEntry]:
    statement = select(VaultEntry).order_by(
        col(VaultEntry.pinned).desc(),
        col(VaultEntry.sort_order),
        col(VaultEntry.id),
    )
    return list(session.exec(statement).all())


def get_entry(session: Session, entry_id: int) -> VaultEntry | None:
    return session.get(VaultEntry, entry_id)


def _next_order(session: Session, section_id: int) -> int:
    max_order = session.exec(
        select(col(VaultEntry.sort_order))
        .where(VaultEntry.section_id == section_id)
        .order_by(col(VaultEntry.sort_order).desc())
    ).first()
    return 0 if max_order is None else int(max_order) + 1


def create_entry(
    session: Session,
    *,
    section_id: int,
    name: str,
    url: str,
    username: str,
    password: str,
    note: str,
) -> VaultEntry:
    row = VaultEntry(
        section_id=section_id,
        name=name,
        url=url,
        username=username,
        password_encrypted=_encrypt(password),
        note=note,
        sort_order=_next_order(session, section_id),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_entry(
    session: Session,
    row: VaultEntry,
    *,
    section_id: int | None = None,
    name: str | None = None,
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    note: str | None = None,
    pinned: bool | None = None,
    locked: bool | None = None,
) -> VaultEntry:
    if section_id is not None and section_id != row.section_id:
        row.section_id = section_id
        row.sort_order = _next_order(session, section_id)
    if name is not None:
        row.name = name
    if url is not None:
        row.url = url
    if username is not None:
        row.username = username
    if password is not None:
        row.password_encrypted = _encrypt(password)
    if note is not None:
        row.note = note
    if pinned is not None:
        row.pinned = pinned
    if locked is not None:
        row.locked = locked
    row.updated_at = utc_now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def pin_to_top(session: Session, row: VaultEntry) -> VaultEntry:
    siblings = session.exec(
        select(VaultEntry).where(VaultEntry.section_id == row.section_id).order_by(col(VaultEntry.sort_order))
    ).all()
    row.sort_order = 0
    session.add(row)
    index = 1
    for item in siblings:
        if item.id == row.id:
            continue
        item.sort_order = index
        session.add(item)
        index += 1
    row.updated_at = utc_now()
    session.commit()
    session.refresh(row)
    return row


def reorder_entries(session: Session, section_id: int, ids: list[int]) -> list[VaultEntry]:
    rows = {
        row.id: row
        for row in session.exec(select(VaultEntry).where(VaultEntry.section_id == section_id)).all()
    }
    for index, entry_id in enumerate(ids):
        row = rows.get(entry_id)
        if row is None:
            continue
        row.sort_order = index
        session.add(row)
    session.commit()
    return list_entries(session)


def delete_entry(session: Session, row: VaultEntry) -> None:
    session.delete(row)
    session.commit()


def _write_entry_blobs(session: Session, blobs: list[tuple[int, str]]) -> None:
    pending = []
    for entry_id, blob in blobs:
        row = get_entry(session, entry_id)
        if row is None:
            session.rollback()
            raise RuntimeError("改密码时找不到条目")
        row.password_encrypted = blob
        row.updated_at = utc_now()
        pending.append(row)
    for row in pending:
        session.add(row)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


def export_plaintext(session: Session, password: str) -> list[dict]:
    salt = vault_kek_salt()
    items = []
    for row in list_entries(session):
        if row.id is None:
            continue
        plain = ""
        if row.password_encrypted:
            try:
                plain = decrypt_text(password, salt, row.password_encrypted, AAD)
            except Exception as exc:
                raise ValueError("密码库有条目解不开，备份已取消") from exc
        items.append({"id": row.id, "password": plain})
    return items


def change_security_password(session: Session, new_password: str, current: str, hint: str | None = None) -> None:
    """Re-encrypt every entry, commit, then store the new hash and salt."""

    from app import privacy

    text = privacy.check_length(new_password)
    found = privacy.security_material()
    current_text = current.strip()
    old_blobs: list[tuple[int, str]] = []
    plains: list[tuple[int, str]] = []
    old_key = None
    if found is not None:
        stored, salt_hex = found
        if not current_text:
            raise PermissionError("请输入当前密码")
        if not verify_password(stored, current_text):
            raise PermissionError("当前密码不对")
        if text == current_text:
            raise ValueError("不能与当前相同")
        old_key = derive_key(current_text, bytes.fromhex(salt_hex))
        try:
            for row in list_entries(session):
                if row.id is None:
                    continue
                plain = ""
                if row.password_encrypted:
                    plain = decrypt_bytes(old_key, bytes.fromhex(row.password_encrypted), AAD).decode("utf-8")
                plains.append((row.id, plain))
                old_blobs.append((row.id, row.password_encrypted))
        except Exception as exc:
            raise ValueError("有条目无法用当前安全密码解密，密码没有修改") from exc
    new_salt = os.urandom(16)
    new_key = derive_key(text, new_salt)
    try:
        new_blobs = [
            (entry_id, encrypt_bytes(new_key, plain.encode("utf-8"), AAD).hex())
            for entry_id, plain in plains
        ]
        if new_blobs:
            _write_entry_blobs(session, new_blobs)
        try:
            privacy.write_security(text, new_salt, hint)
        except Exception:
            if old_blobs:
                _write_entry_blobs(session, old_blobs)
            raise
    finally:
        del new_key
        if old_key is not None:
            del old_key
    privacy.lock()
