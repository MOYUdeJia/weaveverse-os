"""Database operations for imported books."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlmodel import Session, select

from app.book_files import (
    BOOKS_DIR,
    MAX_UPLOAD_BYTES,
    ParsedBook,
    format_for_filename,
    parse_book_file,
    read_book_content,
    remove_book_dir,
    store_book_files,
)
from app.models import Book, utc_now
from app.schemas import BookUpdate


# 整体进度：EPUB 按章节加章内偏移，TXT 就是滚动比例，PDF 保持 0。
# Overall progress: EPUB uses chapter plus in-chapter offset, TXT uses the scroll ratio, PDF stays at 0.
def reading_ratio(book_format: str, chapter_count: int, chapter: int, offset: float) -> float:
    offset = min(1.0, max(0.0, float(offset)))
    if book_format == "txt":
        return round(offset, 6)
    if book_format != "epub" or chapter_count <= 0:
        return 0.0
    bounded = min(max(int(chapter), 0), chapter_count - 1)
    return round(min(1.0, (bounded + offset) / chapter_count), 6)


# 保存上传文件、解析元数据，再写入 books 表。失败时不留半成品目录。
# Store the upload, parse metadata, then insert the books row. A failure leaves no directory behind.
def create_book(session: Session, filename: str, payload: bytes) -> Book:
    original_name = Path(filename or "").name.strip()
    if not original_name or original_name in {".", ".."}:
        raise ValueError("缺少文件名")
    suffix, book_format = format_for_filename(original_name)
    if not payload:
        raise ValueError("空文件")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError("文件超过 100MB")

    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    incoming = BOOKS_DIR / "_incoming"
    incoming.mkdir(exist_ok=True)
    temp_path = incoming / f"{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(payload)
    book_id: int | None = None
    committed = False

    try:
        parsed = parse_book_file(temp_path, book_format, original_name[:255])
        book = _new_book(original_name[:255], book_format, len(payload), parsed)
        session.add(book)
        session.flush()
        book_id = book.id
        store_book_files(book_id, temp_path, suffix, parsed)
        session.commit()
        committed = True
        session.refresh(book)
        return book
    except Exception:
        if not committed:
            session.rollback()
            if book_id is not None:
                remove_book_dir(book_id)
        raise
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


# 按最近阅读、书名或添加时间列出书籍，可按格式筛选。
# List books by recent reading, title, or added time, with an optional format filter.
def list_books(session: Session, *, sort: str, book_format: str | None) -> list[Book]:
    statement = select(Book)
    if book_format:
        statement = statement.where(Book.format == book_format)
    if sort == "title":
        statement = statement.order_by(Book.title, Book.id)
    elif sort == "added":
        statement = statement.order_by(Book.created_at.desc(), Book.id.desc())
    else:
        statement = statement.order_by(
            Book.last_read_at.is_(None),
            Book.last_read_at.desc(),
            Book.created_at.desc(),
            Book.id.desc(),
        )
    return list(session.exec(statement).all())


# 按主键读取一本书。
# Load one book by primary key.
def get_book(session: Session, book_id: int) -> Book | None:
    return session.get(Book, book_id)


# 更新书名、作者或阅读位置。只改进度时才刷新 last_read_at。
# Update title, author, or reading position. last_read_at changes only when progress changes.
def update_book(session: Session, book: Book, data: BookUpdate) -> Book:
    progress_sent = data.progress_chapter is not None or data.progress_offset is not None
    if progress_sent:
        _apply_progress(book, data)

    if data.title is not None:
        book.title = data.title
    if data.author is not None:
        book.author = data.author

    book.updated_at = utc_now()
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


# 先删目录，再删行。目录删不掉时保留记录，方便重试。
# Remove the directory first, then the row. If the directory remains, keep the row so delete can be retried.
def delete_book(session: Session, book: Book) -> None:
    remove_book_dir(book.id)
    session.delete(book)
    session.commit()


# 取出某一章的正文，或 PDF 的外部打开说明。
# Return one chapter body, or the external-open payload for a PDF.
def book_content(book: Book, chapter: int) -> dict:
    if book.format == "pdf" and chapter != 0:
        raise ValueError("PDF 没有章节")
    try:
        return read_book_content(
            book.id,
            book.format,
            chapter=0 if book.format == "pdf" else chapter,
            toc=_load_toc(book.toc),
            text_encoding=book.text_encoding,
            title=book.title,
            page_count=book.page_count,
        )
    except FileNotFoundError as exc:
        raise ValueError("书籍文件丢失") from exc
    except IndexError as exc:
        raise IndexError("章节不存在") from exc


# 列表和详情共用的字段。
# Fields shared by the list and detail payloads.
def book_to_summary(book: Book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "format": book.format,
        "original_filename": book.original_filename,
        "file_size": book.file_size,
        "has_cover": bool(book.cover_ext),
        "language": book.language,
        "chapter_count": book.chapter_count,
        "page_count": book.page_count,
        "progress_chapter": book.progress_chapter,
        "progress_offset": book.progress_offset,
        "progress_ratio": book.progress_ratio,
        "last_read_at": book.last_read_at,
        "created_at": book.created_at,
        "updated_at": book.updated_at,
    }


# 详情比列表多了简介和目录标题。
# Detail adds the description and chapter titles.
def book_to_detail(book: Book) -> dict:
    detail = book_to_summary(book)
    detail["description"] = book.description
    detail["toc"] = [
        {"index": item["index"], "title": item["title"]}
        for item in _load_toc(book.toc)
    ]
    return detail


def _new_book(original_name: str, book_format: str, file_size: int, parsed: ParsedBook) -> Book:
    return Book(
        title=parsed.title,
        author=parsed.author,
        format=book_format,
        original_filename=original_name,
        file_size=file_size,
        cover_ext=parsed.cover_ext,
        language=parsed.language,
        description=parsed.description,
        text_encoding=parsed.text_encoding,
        chapter_count=parsed.chapter_count,
        page_count=parsed.page_count,
        toc=json.dumps(parsed.toc, ensure_ascii=False),
    )


def _apply_progress(book: Book, data: BookUpdate) -> None:
    if book.format == "pdf":
        raise ValueError("PDF 不记录阅读位置")

    chapter = book.progress_chapter if data.progress_chapter is None else data.progress_chapter
    if data.progress_chapter is not None and data.progress_offset is None:
        offset = 0.0
    else:
        offset = book.progress_offset if data.progress_offset is None else data.progress_offset

    if book.format == "txt" and chapter != 0:
        raise ValueError("TXT 只有一章")
    if book.format == "epub" and chapter >= book.chapter_count:
        raise ValueError("章节不存在")

    book.progress_chapter = chapter
    book.progress_offset = offset
    book.progress_ratio = reading_ratio(book.format, book.chapter_count, chapter, offset)
    book.last_read_at = utc_now()


def _load_toc(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    toc: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        toc.append(
            {
                "index": int(item.get("index", len(toc))),
                "title": str(item.get("title") or ""),
                "href": str(item.get("href") or ""),
            }
        )
    return toc
