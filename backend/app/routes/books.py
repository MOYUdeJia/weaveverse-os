"""HTTP routes for the bookshelf: upload, list, detail, update, delete, cover, and content."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from app import book_crud
from app.book_files import COVER_MEDIA_BY_EXT, MAX_UPLOAD_BYTES, cover_path
from app.db import get_session
from app.errors import raise_api_error
from app.schemas import BookContent, BookDetail, BookSummary, BookUpdate


router = APIRouter(prefix="/books", tags=["books"])

SORTS = {"recent", "title", "added"}
FORMATS = {"epub", "txt", "pdf"}


@router.get("", response_model=list[BookSummary])
# 书架列表。sort=recent|title|added，format 可省略。
# Bookshelf list. sort is recent, title, or added. format is optional.
def get_books(sort: str = "recent", format: str | None = None, session: Session = Depends(get_session)):
    if sort not in SORTS:
        raise_api_error(400, "sort", "sort 只能是 recent、title 或 added")
    if format is not None and format not in FORMATS:
        raise_api_error(400, "format", "format 只能是 epub、txt 或 pdf")
    return [book_crud.book_to_summary(book) for book in book_crud.list_books(session, sort=sort, book_format=format)]


@router.post("", response_model=BookDetail, status_code=201)
# 上传一本书并返回解析后的详情。
# Upload one book and return its parsed detail.
async def upload_book(file: UploadFile, session: Session = Depends(get_session)):
    payload = await _read_upload(file)
    try:
        book = book_crud.create_book(session, file.filename or "", payload)
    except ValueError as exc:
        raise_api_error(400, "file", str(exc))
    return book_crud.book_to_detail(book)


@router.get("/{book_id}", response_model=BookDetail)
# 一本书的详情，含目录标题。
# Detail for one book, including chapter titles.
def get_book(book_id: int, session: Session = Depends(get_session)):
    book = _require_book(session, book_id)
    return book_crud.book_to_detail(book)


@router.patch("/{book_id}", response_model=BookDetail)
# 修改书名、作者或阅读进度。
# Update the title, author, or reading progress.
def patch_book(book_id: int, data: BookUpdate, session: Session = Depends(get_session)):
    if data.title is None and data.author is None and data.progress_chapter is None and data.progress_offset is None:
        raise_api_error(400, "body", "至少提供一个字段")
    book = _require_book(session, book_id)
    try:
        updated = book_crud.update_book(session, book, data)
    except ValueError as exc:
        if data.progress_chapter is not None:
            field = "progress_chapter"
        elif data.progress_offset is not None:
            field = "progress_offset"
        else:
            field = "body"
        raise_api_error(400, field, str(exc))
    return book_crud.book_to_detail(updated)


@router.delete("/{book_id}")
# 删除书籍记录和 data/books/{id}/ 目录。
# Delete the book row and its data/books/{id}/ directory.
def remove_book(book_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    book = _require_book(session, book_id)
    try:
        book_crud.delete_book(session, book)
    except OSError:
        raise_api_error(500, "file", "书籍文件删除失败")
    return {"status": "ok"}


@router.get("/{book_id}/cover")
# 返回提取出的封面。没有封面时 404，前端用占位图。
# Return the extracted cover. A missing cover is 404 so the frontend can draw a placeholder.
def get_cover(book_id: int, session: Session = Depends(get_session)):
    book = _require_book(session, book_id)
    path = cover_path(book.id, book.cover_ext)
    if path is None or not path.is_file():
        raise_api_error(404, "cover", "这本书没有封面")
    return FileResponse(path, media_type=COVER_MEDIA_BY_EXT[book.cover_ext])


@router.get("/{book_id}/content", response_model=BookContent)
# EPUB / TXT 返回正文。PDF 只说明需要用系统应用打开。
# Return EPUB or TXT body text. PDF only reports that the system app should open it.
def get_content(book_id: int, chapter: int = 0, session: Session = Depends(get_session)):
    if chapter < 0:
        raise_api_error(400, "chapter", "章节不存在")
    book = _require_book(session, book_id)
    try:
        return book_crud.book_content(book, chapter)
    except IndexError:
        raise_api_error(400, "chapter", "章节不存在")
    except ValueError as exc:
        raise_api_error(400, "chapter", str(exc))


# 分块读取后仍拼成完整字节，不是流式落盘。超过 100MB 立即拒绝。
# Chunks are joined into one buffer, not streamed to disk. Reject anything over 100MB.
async def _read_upload(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise_api_error(400, "file", "文件超过 100MB")
        chunks.append(chunk)
    return b"".join(chunks)


# 书籍不存在时返回统一的 404。
# Return the shared 404 when a book id is missing.
def _require_book(session: Session, book_id: int):
    book = book_crud.get_book(session, book_id)
    if book is None:
        raise_api_error(404, "id", "书籍不存在")
    return book
