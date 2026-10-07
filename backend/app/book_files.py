"""Read and store imported book files.

EPUB metadata, cover, and chapter HTML come from ebooklib. TXT is decoded
locally. PDF metadata comes from pypdf; the original file is kept for the
system viewer and is not turned into HTML.
"""

from __future__ import annotations

import re
import shutil
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

import ebooklib
from ebooklib import epub
from ebooklib.epub import EpubException
from lxml.etree import XMLSyntaxError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import BOOKS_DIR


MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_EPUB_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 8000

FORMAT_BY_SUFFIX = {".epub": "epub", ".txt": "txt", ".pdf": "pdf"}
COVER_EXT_BY_MEDIA = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}
COVER_MEDIA_BY_EXT = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}
TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5")
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass
class ParsedBook:
    """Metadata extracted before a book row is stored."""

    title: str
    author: str
    language: str = ""
    description: str = ""
    text_encoding: str = ""
    chapter_count: int = 0
    page_count: int = 0
    toc: list[dict] = field(default_factory=list)
    cover_ext: str | None = None
    cover_bytes: bytes | None = None


# 上传后缀只接受 epub / txt / pdf。
# Accept only epub, txt, and pdf upload suffixes.
def format_for_filename(filename: str) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    book_format = FORMAT_BY_SUFFIX.get(suffix)
    if book_format is None:
        raise ValueError("仅支持 epub / txt / pdf")
    return suffix, book_format


# 一本书的目录：data/books/{id}/。
# Directory for one book: data/books/{id}/.
def book_dir(book_id: int) -> Path:
    return BOOKS_DIR / str(book_id)


# 原始文件路径。扩展名与格式一致。
# Path of the stored original. The suffix matches the format.
def original_path(book_id: int, book_format: str) -> Path:
    return book_dir(book_id) / f"original.{book_format}"


# 封面路径。没有封面时返回 None。
# Cover path, or None when this book has no extracted cover.
def cover_path(book_id: int, cover_ext: str | None) -> Path | None:
    if not cover_ext or cover_ext not in COVER_MEDIA_BY_EXT:
        return None
    return book_dir(book_id) / f"cover.{cover_ext}"


# 删掉一本书的整个目录。目录不存在时直接返回。
# Remove one book's directory. Missing directories are ignored.
def remove_book_dir(book_id: int) -> None:
    target = book_dir(book_id)
    if target.exists():
        shutil.rmtree(target)


# 把临时文件挪进 books/{id}/，并写出封面。
# Move the temp upload into books/{id}/ and write the cover beside it.
def store_book_files(book_id: int, source: Path, suffix: str, parsed: ParsedBook) -> None:
    target = book_dir(book_id)
    target.mkdir(parents=True, exist_ok=False)
    shutil.move(str(source), target / f"original{suffix}")
    if parsed.cover_bytes and parsed.cover_ext:
        (target / f"cover.{parsed.cover_ext}").write_bytes(parsed.cover_bytes)


# 按后缀解析已经落盘的上传文件。
# Parse an uploaded file already written to disk.
def parse_book_file(path: Path, book_format: str, original_filename: str) -> ParsedBook:
    fallback_title = _clip(_stem(original_filename) or "未命名", MAX_TITLE_LENGTH)
    if book_format == "epub":
        return _parse_epub(path, fallback_title)
    if book_format == "txt":
        return _parse_txt(path, fallback_title)
    if book_format == "pdf":
        return _parse_pdf(path, fallback_title)
    raise ValueError("仅支持 epub / txt / pdf")


# 读取某一章。PDF 不返回正文。
# Read one chapter. PDF content stays external.
def read_book_content(book_id: int, book_format: str, *, chapter: int, toc: list[dict], text_encoding: str, title: str, page_count: int) -> dict:
    path = original_path(book_id, book_format)
    if not path.is_file():
        raise FileNotFoundError(path)

    if book_format == "pdf":
        return {
            "format": "pdf",
            "chapter": None,
            "title": title,
            "chapter_count": 0,
            "html": None,
            "text": None,
            "external": True,
            "page_count": page_count,
        }

    if chapter < 0 or chapter >= len(toc):
        raise IndexError(chapter)

    entry = toc[chapter]
    if book_format == "txt":
        text = path.read_bytes().decode(text_encoding or "utf-8")
        return {
            "format": "txt",
            "chapter": 0,
            "title": entry.get("title") or title,
            "chapter_count": 1,
            "html": None,
            "text": text,
            "external": False,
            "page_count": 0,
        }

    html = _read_epub_html(path, str(entry.get("href") or ""))
    return {
        "format": "epub",
        "chapter": chapter,
        "title": entry.get("title") or title,
        "chapter_count": len(toc),
        "html": html,
        "text": None,
        "external": False,
        "page_count": 0,
    }


# 用文件名去掉后缀作为缺省书名。
# Use the filename without its suffix as the fallback title.
def _stem(filename: str) -> str:
    return Path(filename).stem.strip()


def _clip(value: str, limit: int) -> str:
    return value.strip()[:limit]


def _plain(value: str) -> str:
    text = _TAG_RE.sub(" ", value or "")
    return _SPACE_RE.sub(" ", text).strip()


def _decode_text(payload: bytes) -> tuple[str, str]:
    for encoding in TEXT_ENCODINGS:
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别文本编码，请使用 UTF-8、GB18030 或 Big5")


def _meta_rows(book: epub.EpubBook, namespace: str, name: str) -> list[tuple]:
    try:
        rows = book.get_metadata(namespace, name) or []
    except KeyError:
        return []
    return list(rows)


def _meta_texts(book: epub.EpubBook, namespace: str, name: str) -> list[str]:
    texts: list[str] = []
    for value, _others in _meta_rows(book, namespace, name):
        text = _plain("" if value is None else str(value))
        if text:
            texts.append(text)
    return texts


def _norm_href(href: str) -> str:
    cleaned = unquote(href.split("#", 1)[0]).replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned.lstrip("/")


def _iter_toc(nodes) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for node in nodes or []:
        if isinstance(node, tuple) and len(node) == 2:
            section, children = node
            href = getattr(section, "href", "") or ""
            title = getattr(section, "title", "") or ""
            if href:
                pairs.append((href, title))
            pairs.extend(_iter_toc(children))
            continue
        href = getattr(node, "href", "") or ""
        title = getattr(node, "title", "") or ""
        if href:
            pairs.append((href, title))
    return pairs


def _title_for(file_name: str, pairs: list[tuple[str, str]], index: int) -> str:
    key = _norm_href(file_name)
    for href, title in pairs:
        href_key = _norm_href(href)
        if href_key == key or href_key.endswith("/" + key) or key.endswith("/" + href_key):
            cleaned = title.strip()
            if cleaned:
                return _clip(cleaned, MAX_TITLE_LENGTH)
    return f"第{index + 1}章"


def _cover_ext(media_type: str, payload: bytes) -> str | None:
    ext = COVER_EXT_BY_MEDIA.get((media_type or "").split(";", 1)[0].strip().lower())
    if ext:
        return ext
    if payload.startswith(b"\xff\xd8"):
        return "jpg"
    if payload.startswith(b"\x89PNG"):
        return "png"
    if payload.startswith(b"GIF8"):
        return "gif"
    if payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return "webp"
    return None


def _image_bytes(item) -> tuple[str, bytes] | None:
    payload = item.get_content() or b""
    if not payload:
        return None
    ext = _cover_ext(getattr(item, "media_type", "") or "", payload)
    if ext is None:
        return None
    return ext, payload


def _find_cover(book: epub.EpubBook) -> tuple[str, bytes] | None:
    for _value, others in _meta_rows(book, "OPF", "cover"):
        cover_id = (others or {}).get("content")
        if not cover_id:
            continue
        item = book.get_item_with_id(cover_id)
        if item is None:
            continue
        found = _image_bytes(item)
        if found:
            return found

    for item in book.get_items_of_type(ebooklib.ITEM_COVER):
        found = _image_bytes(item)
        if found:
            return found

    for guide in book.guide or []:
        if guide.get("type") != "cover":
            continue
        href = _norm_href(guide.get("href") or "")
        for item in book.get_items():
            if _norm_href(item.get_name()) == href:
                found = _image_bytes(item)
                if found:
                    return found

    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        if "cover" in item.get_name().lower():
            found = _image_bytes(item)
            if found:
                return found
    return None


def _parse_epub(path: Path, fallback_title: str) -> ParsedBook:
    _guard_epub_zip(path)
    try:
        book = _open_epub(path)
    except (EpubException, zipfile.BadZipFile, KeyError, OSError, XMLSyntaxError) as exc:
        raise ValueError("无法解析 EPUB") from exc

    titles = _meta_texts(book, "DC", "title")
    authors = _meta_texts(book, "DC", "creator")
    languages = _meta_texts(book, "DC", "language")
    descriptions = _meta_texts(book, "DC", "description")
    toc_pairs = _iter_toc(book.toc)
    chapters: list[dict] = []

    spine = list(book.spine or [])
    idrefs = [idref for idref, linear in spine if linear != "no" and idref]
    if not idrefs:
        idrefs = [idref for idref, _linear in spine if idref]

    for idref in idrefs:
        item = book.get_item_with_id(idref)
        if item is None or not isinstance(item, epub.EpubHtml) or not item.is_chapter():
            continue
        chapters.append(
            {
                "index": len(chapters),
                "title": _title_for(item.get_name(), toc_pairs, len(chapters)),
                "href": item.get_name(),
            }
        )

    if not chapters:
        raise ValueError("EPUB 里没有可阅读的章节")

    cover = _find_cover(book)
    return ParsedBook(
        title=_clip(titles[0], MAX_TITLE_LENGTH) if titles else fallback_title,
        author=_clip(", ".join(authors), MAX_AUTHOR_LENGTH),
        language=_clip(languages[0], 32) if languages else "",
        description=_clip(descriptions[0], MAX_DESCRIPTION_LENGTH) if descriptions else "",
        chapter_count=len(chapters),
        toc=chapters,
        cover_ext=cover[0] if cover else None,
        cover_bytes=cover[1] if cover else None,
    )


def _guard_epub_zip(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if not any(name.endswith("META-INF/container.xml") for name in names):
                raise ValueError("不是有效的 EPUB")
            total = 0
            for info in archive.infolist():
                total += info.file_size
                if total > MAX_EPUB_UNCOMPRESSED_BYTES:
                    raise ValueError("EPUB 解压后超过 200MB")
    except zipfile.BadZipFile as exc:
        raise ValueError("不是有效的 EPUB") from exc


def _open_epub(path: Path):
    # 0.18 仍会读 NCX。显式关掉 ignore_ncx，避免以后默认值改掉目录标题。
    # 0.18 still reads NCX. Pin ignore_ncx off so a future default does not drop titles.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", module=r"ebooklib(\.|$)")
        return epub.read_epub(str(path), options={"ignore_ncx": False})


def _read_epub_html(path: Path, href: str) -> str:
    try:
        book = _open_epub(path)
    except (EpubException, zipfile.BadZipFile, KeyError, OSError, XMLSyntaxError) as exc:
        raise ValueError("无法读取 EPUB 章节") from exc

    item = book.get_item_with_href(href) if href else None
    if item is None:
        raise ValueError("章节内容丢失")

    body = b""
    if hasattr(item, "get_body_content"):
        body = item.get_body_content() or b""
    if isinstance(body, str):
        body = body.encode("utf-8")
    payload = body if body.strip() else (item.get_content() or b"")
    text, _encoding = _decode_text(payload)
    return text


def _parse_txt(path: Path, fallback_title: str) -> ParsedBook:
    text, encoding = _decode_text(path.read_bytes())
    if not text.strip():
        raise ValueError("空文件")
    return ParsedBook(
        title=fallback_title,
        author="",
        text_encoding=encoding,
        chapter_count=1,
        toc=[{"index": 0, "title": fallback_title, "href": ""}],
    )


def _parse_pdf(path: Path, fallback_title: str) -> ParsedBook:
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError("加密的 PDF 无法读取元数据")
        meta = reader.metadata
        page_count = len(reader.pages)
    except ValueError:
        raise
    except (PdfReadError, OSError) as exc:
        raise ValueError("无法解析 PDF") from exc

    title = _pdf_text(getattr(meta, "title", None)) if meta is not None else ""
    author = _pdf_text(getattr(meta, "author", None)) if meta is not None else ""
    return ParsedBook(
        title=_clip(title, MAX_TITLE_LENGTH) if title else fallback_title,
        author=_clip(author, MAX_AUTHOR_LENGTH),
        page_count=page_count,
    )


def _pdf_text(value) -> str:
    if value is None:
        return ""
    return _plain(str(value).replace("\x00", ""))
