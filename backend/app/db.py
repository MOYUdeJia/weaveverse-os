"""SQLite engine and session helpers for the Weaveverse backend."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import event
from sqlmodel import Session, create_engine

from app.config import DATABASE_URL


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


# 在每个 SQLite 连接上打开外键，让 ON DELETE CASCADE 生效。
# Enable foreign keys on every SQLite connection so ON DELETE CASCADE works.
@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# 为 FastAPI 请求提供一个 SQLModel 会话。
# Yield one SQLModel session for a FastAPI request.
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
