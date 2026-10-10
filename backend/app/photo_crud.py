"""Metadata operations for photos and albums.

Files stay in attachments. Deleting a photo or an album does not delete files.
"""

from __future__ import annotations

from sqlmodel import Session, col, select

from app.album_lock import check_album_password, clear_album_password, set_album_password
from app.models import PhotoAlbum, PhotoLibrary, utc_now

ALBUM_COLORS = ["#3f6f57", "#d77245", "#5c79a8", "#7a4e7a", "#3ca1b0", "#e2b340"]


def album_to_dict(row: PhotoAlbum) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "cover_filename": row.cover_filename,
        "is_private": row.is_private,
        "color": row.color or "",
        "sort_order": row.sort_order,
        "created_at": row.created_at,
    }


def photo_to_dict(row: PhotoLibrary) -> dict:
    return {
        "id": row.id,
        "filename": row.filename,
        "note": row.note,
        "display_name": row.display_name or "",
        "album_id": row.album_id,
        "added_at": row.added_at,
    }


def get_album(session: Session, album_id: int) -> PhotoAlbum | None:
    return session.get(PhotoAlbum, album_id)


def list_albums(session: Session) -> list[PhotoAlbum]:
    statement = select(PhotoAlbum).order_by(col(PhotoAlbum.sort_order), col(PhotoAlbum.id))
    rows = list(session.exec(statement).all())
    changed = False
    for index, row in enumerate(rows):
        if not row.color:
            row.color = ALBUM_COLORS[index % len(ALBUM_COLORS)]
            session.add(row)
            changed = True
    if changed:
        session.commit()
        for row in rows:
            session.refresh(row)
    return rows


def reorder_albums(session: Session, ids: list[int]) -> list[PhotoAlbum]:
    rows = {row.id: row for row in list_albums(session)}
    for index, album_id in enumerate(ids):
        row = rows.get(album_id)
        if row is None:
            continue
        row.sort_order = index
        session.add(row)
    session.commit()
    return list_albums(session)


def create_album(session: Session, name: str, is_private: bool, password: str, color: str = "") -> PhotoAlbum:
    max_order = session.exec(select(col(PhotoAlbum.sort_order)).order_by(col(PhotoAlbum.sort_order).desc())).first()
    next_order = 0 if max_order is None else int(max_order) + 1
    picked = color if color in ALBUM_COLORS else ALBUM_COLORS[next_order % len(ALBUM_COLORS)]
    row = PhotoAlbum(
        name=name,
        is_private=is_private,
        color=picked,
        sort_order=next_order,
        created_at=utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    if is_private and row.id is not None:
        set_album_password(row.id, password)
    return row


def update_album(
    session: Session,
    row: PhotoAlbum,
    *,
    name: str | None,
    is_private: bool | None,
    password: str | None,
) -> PhotoAlbum:
    if name is not None:
        row.name = name
    if is_private is True:
        if not password:
            raise ValueError("请设置密码")
        row.is_private = True
        if row.id is not None:
            set_album_password(row.id, password)
    elif is_private is False:
        row.is_private = False
        if row.id is not None:
            clear_album_password(row.id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_album(session: Session, row: PhotoAlbum) -> None:
    photos = session.exec(select(PhotoLibrary).where(PhotoLibrary.album_id == row.id)).all()
    for photo in photos:
        photo.album_id = None
        session.add(photo)
    if row.id is not None:
        clear_album_password(row.id)
    session.delete(row)
    session.commit()


def album_allows(session: Session, album_id: int | None, password: str | None) -> PhotoAlbum | None:
    album = get_album(session, album_id)
    if album is None:
        raise LookupError("相册不存在")
    if album.is_private and not check_album_password(album.id or 0, password or ""):
        raise PermissionError("需要密码")
    return album


def get_photo(session: Session, photo_id: int) -> PhotoLibrary | None:
    return session.get(PhotoLibrary, photo_id)


def get_photo_by_filename(session: Session, filename: str) -> PhotoLibrary | None:
    return session.exec(select(PhotoLibrary).where(PhotoLibrary.filename == filename)).first()


def list_photos(session: Session, album_id: int | None, password: str | None) -> list[PhotoLibrary]:
    if album_id is None:
        private_ids = list(
            session.exec(select(PhotoAlbum.id).where(PhotoAlbum.is_private == True)).all()  # noqa: E712
        )
        statement = select(PhotoLibrary)
        if private_ids:
            statement = statement.where(
                (PhotoLibrary.album_id == None) | col(PhotoLibrary.album_id).not_in(private_ids)  # noqa: E711
            )
    else:
        album_allows(session, album_id, password)
        statement = select(PhotoLibrary).where(PhotoLibrary.album_id == album_id)
    statement = statement.order_by(col(PhotoLibrary.added_at).desc(), col(PhotoLibrary.id).desc())
    return list(session.exec(statement).all())


def add_photo(
    session: Session,
    filename: str,
    note: str = "",
    album_id: int | None = None,
    password: str | None = None,
) -> PhotoLibrary:
    if album_id is not None:
        album = get_album(session, album_id)
        if album is None:
            raise LookupError("相册不存在")
        if album.is_private and not check_album_password(album.id or 0, password or ""):
            raise PermissionError("需要密码")
    existing = get_photo_by_filename(session, filename)
    if existing is not None:
        existing.album_id = album_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    row = PhotoLibrary(filename=filename, note=note, display_name=note, album_id=album_id, added_at=utc_now())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def rename_photo(session: Session, row: PhotoLibrary, display_name: str) -> PhotoLibrary:
    row.display_name = display_name
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def move_photos(session: Session, ids: list[int], album_id: int | None, password: str | None) -> int:
    if album_id is not None:
        album_allows(session, album_id, password)
    count = 0
    for photo_id in ids:
        row = get_photo(session, photo_id)
        if row is None:
            continue
        row.album_id = album_id
        session.add(row)
        count += 1
    session.commit()
    return count


def delete_photos(session: Session, ids: list[int]) -> int:
    count = 0
    for photo_id in ids:
        row = get_photo(session, photo_id)
        if row is None:
            continue
        session.delete(row)
        count += 1
    session.commit()
    return count


def delete_photo(session: Session, row: PhotoLibrary) -> None:
    session.delete(row)
    session.commit()
