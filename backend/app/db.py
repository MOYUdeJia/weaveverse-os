"""SQLite engine and session helpers for the Weaveverse backend."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.config import DATABASE_URL


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def get_session() -> Generator[Session, None, None]:
    """Yield one SQLModel session for a FastAPI request."""
    with Session(engine) as session:
        yield session
