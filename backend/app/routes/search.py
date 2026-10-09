"""HTTP route for library search."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.search import search_library


router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
# 按标题、分组、书籍和区块正文做子串搜索。
# Substring search over titles, groups, books, and block content.
def get_search(q: str = "", session: Session = Depends(get_session)) -> dict:
    return search_library(session, q)
