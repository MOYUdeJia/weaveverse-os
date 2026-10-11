"""Find attachment files that nothing in the workspace still mentions."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from sqlmodel import Session, select

from app.appearance import load_settings
from app.book_files import cover_path
from app.config import ATTACHMENTS_DIR, DATA_DIR
from app.models import Block, Book, Group, Idea, NavItem, PhotoAlbum, PhotoLibrary


def _blobs(session: Session) -> list[tuple[str, str]]:
    blobs: list[tuple[str, str]] = []
    for block in session.exec(select(Block)).all():
        blobs.append((f"block:{block.id}", block.content or ""))
    for photo in session.exec(select(PhotoLibrary)).all():
        blobs.append((f"photo:{photo.id}", photo.filename or ""))
    for album in session.exec(select(PhotoAlbum)).all():
        blobs.append((f"album:{album.id}", album.cover_filename or ""))
    for idea in session.exec(select(Idea)).all():
        blobs.append((f"idea:{idea.id}", f"{idea.title}\n{idea.content}"))
    for item in session.exec(select(NavItem)).all():
        blobs.append((f"nav:{item.id}", item.icon or ""))
    for group in session.exec(select(Group)).all():
        blobs.append((f"group:{group.id}", group.icon or ""))
    for book in session.exec(select(Book)).all():
        cover = cover_path(book.id, book.cover_ext)
        blobs.append((f"book:{book.id}", cover.name if cover else ""))
    try:
        appearance = DATA_DIR.joinpath("appearance.json").read_text(encoding="utf-8")
    except OSError:
        appearance = ""
    blobs.append(("appearance", appearance))
    settings = load_settings()
    blobs.append(("appearance_settings", str(settings)))
    return blobs


def reference_map(session: Session) -> dict[str, list[str]]:
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    names = [path.name for path in ATTACHMENTS_DIR.iterdir() if path.is_file()]
    found: dict[str, list[str]] = defaultdict(list)
    blobs = _blobs(session)
    for name in names:
        for source, text in blobs:
            if name and name in text:
                found[name].append(source)
    return found


def unused_files(session: Session) -> list[dict]:
    used = reference_map(session)
    items = []
    for path in sorted(ATTACHMENTS_DIR.iterdir()):
        if not path.is_file():
            continue
        if used.get(path.name):
            continue
        items.append({"filename": path.name, "size": path.stat().st_size})
    return items


def count_other_refs(session: Session, filename: str, photo_id: int | None) -> int:
    skip = {f"photo:{photo_id}"} if photo_id is not None else set()
    return len([source for source in reference_map(session).get(filename, []) if source not in skip])


def purge_files(session: Session, filenames: list[str]) -> list[str]:
    used = reference_map(session)
    removed = []
    for raw in filenames:
        name = Path(raw).name
        if name != raw or name in {"", ".", ".."}:
            continue
        if used.get(name):
            continue
        path = ATTACHMENTS_DIR / name
        if path.is_file():
            path.unlink()
            removed.append(name)
    return removed
