"""Stored ideas for the single idea box page."""

from __future__ import annotations

import json

from sqlmodel import Session, col, select

from app.models import Idea, utc_now


def _tags(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    cleaned = []
    for item in data:
        text = str(item).strip().lstrip("#")
        if text and text not in cleaned:
            cleaned.append(text[:24])
    return cleaned[:8]


def idea_to_dict(row: Idea) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "content": row.content,
        "tags": _tags(row.tags),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_ideas(session: Session) -> list[Idea]:
    statement = select(Idea).order_by(col(Idea.updated_at).desc(), col(Idea.id).desc())
    return list(session.exec(statement).all())


def get_idea(session: Session, idea_id: int) -> Idea | None:
    return session.get(Idea, idea_id)


def create_idea(session: Session, title: str, content: str, tags: list[str]) -> Idea:
    row = Idea(title=title, content=content, tags=json.dumps(tags, ensure_ascii=False), created_at=utc_now(), updated_at=utc_now())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_idea(session: Session, row: Idea, title: str | None, content: str | None, tags: list[str] | None) -> Idea:
    if title is not None:
        row.title = title
    if content is not None:
        row.content = content
    if tags is not None:
        row.tags = json.dumps(tags, ensure_ascii=False)
    row.updated_at = utc_now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_idea(session: Session, row: Idea) -> None:
    session.delete(row)
    session.commit()
