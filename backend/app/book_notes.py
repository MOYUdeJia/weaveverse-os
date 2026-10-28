"""Queries for highlights, underlines, notes, and bookmarks on a book."""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import BookNote, utc_now


NOTE_TYPES = {"highlight", "underline", "note", "bookmark"}
NOTE_COLORS = {"gold", "moss", "sky", "rose"}


def list_notes(session: Session, book_id: int) -> list[BookNote]:
    statement = select(BookNote).where(BookNote.book_id == book_id).order_by(BookNote.created_at, BookNote.id)
    return list(session.exec(statement).all())


def note_to_dict(note: BookNote) -> dict:
    return {
        "id": note.id,
        "book_id": note.book_id,
        "position": note.position,
        "type": note.type,
        "color": note.color,
        "text": note.text,
        "note_content": note.note_content,
        "created_at": note.created_at,
    }


def create_note(session: Session, book_id: int, data: dict) -> BookNote:
    note = BookNote(
        book_id=book_id,
        position=str(data.get("position") or "")[:4000],
        type=str(data.get("type") or ""),
        color=str(data.get("color") or "")[:16],
        text=str(data.get("text") or "")[:4000],
        note_content=str(data.get("note_content") or "")[:4000],
        created_at=utc_now(),
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def delete_note(session: Session, book_id: int, note_id: int) -> bool:
    note = session.get(BookNote, note_id)
    if note is None or note.book_id != book_id:
        return False
    session.delete(note)
    session.commit()
    return True


def delete_notes_for_book(session: Session, book_id: int) -> None:
    notes = list_notes(session, book_id)
    for note in notes:
        session.delete(note)
