"""Move the data folder, then empty the old one.

The location pointer lives outside the data folder. A failed copy never writes
that pointer. Whisper models and old pre-m5 backups are not copied; they can
be downloaded again. After a good copy, the old folder keeps only pointer
files (location.txt, .data-location, .pending-delete). Everything else,
including whisper_models and safety, is removed once database handles are
released. If a file is still locked, the pending marker stays for the next
startup.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.config import DATA_DIR, DATABASE_PATH, default_data_dir, location_file, pending_delete_file


SKIP_NAMES = {".weaveverse-port", "_backup_snapshot.db"}
SKIP_SUFFIXES = {".db-wal", ".db-shm"}
SKIP_DIRS = {"whisper_models"}
# Files that point at a data folder. They are not copied and not deleted.
POINTER_NAMES = {".data-location", "location.txt", ".pending-delete"}


def describe_data_dir() -> dict:
    pointer = location_file()
    custom = False
    try:
        custom = bool(pointer.read_text(encoding="utf-8").strip())
    except OSError:
        custom = False
    return {
        "path": str(DATA_DIR),
        "default_path": str(default_data_dir()),
        "custom": custom,
    }


def _nested(left: Path, right: Path) -> bool:
    try:
        left.resolve().relative_to(right.resolve())
    except ValueError:
        return False
    return True


def _reject_path(target: Path) -> str | None:
    if not target.is_absolute():
        return "请选择一个绝对路径"
    if target.resolve() == DATA_DIR.resolve():
        return "这已经是当前数据目录"
    if _nested(target, DATA_DIR) or _nested(DATA_DIR, target):
        return "新目录不能放在当前数据目录里面，也不能包住它"
    blocked = {"windows", "program files", "program files (x86)", "system32"}
    if target.name.lower() in blocked or any(part.lower() in {"windows", "system32"} for part in target.parts):
        return "不能迁到系统目录"
    if len(target.parts) < 2:
        return "请选一个具体文件夹，不要选整块磁盘"
    if target.exists() and any(target.iterdir()):
        return "目标文件夹不是空的"
    return None


def _checkpoint() -> None:
    from app.db import engine

    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA wal_checkpoint(FULL)")


def _pointer(path: Path, root: Path) -> bool:
    return path.is_file() and path.parent == root and path.name in POINTER_NAMES


def _skipped(path: Path, root: Path) -> bool:
    """True when a path is not part of the copy. It is still removed afterwards."""
    relative = path.relative_to(root)
    if _pointer(path, root):
        return True
    if any(part in SKIP_DIRS for part in relative.parts):
        return True
    if path.name in SKIP_NAMES or path.name.endswith(".pre-m5.db"):
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in SKIP_DIRS or name in SKIP_NAMES or name in POINTER_NAMES or name.endswith(".pre-m5.db"):
            ignored.add(name)
        elif Path(name).suffix.lower() in SKIP_SUFFIXES:
            ignored.add(name)
    return ignored


def _manifest(root: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    if not root.exists():
        return rows
    for path in root.rglob("*"):
        if not path.is_file() or _skipped(path, root):
            continue
        rows.append((path.relative_to(root).as_posix(), path.stat().st_size))
    return sorted(rows)


def _verify_copy(source: Path, dest: Path) -> str | None:
    if _manifest(source) != _manifest(dest):
        return "复制后的文件和原来不一致"
    database = dest / "weaveverse.db"
    if not database.is_file():
        return "新目录里没有数据库"
    connection = sqlite3.connect(database)
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        count = connection.execute("SELECT COUNT(*) FROM nav_items").fetchone()
    except sqlite3.Error:
        return "新数据库打不开"
    finally:
        connection.close()
    if not row or row[0] != "ok":
        return "新数据库校验没有通过"
    if count is None:
        return "新数据库缺少导航表"
    return None


def move_data_dir(raw_path: str) -> dict:
    target = Path(str(raw_path or "").strip())
    reason = _reject_path(target)
    if reason:
        raise ValueError(reason)

    source = DATA_DIR.resolve()
    if not source.is_dir():
        raise ValueError("当前数据目录不存在")

    owned = (not target.exists()) or (not any(target.iterdir()))
    _checkpoint()
    try:
        target.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            if _skipped(child, source):
                continue
            dest_child = target / child.name
            if child.is_dir():
                shutil.copytree(child, dest_child, dirs_exist_ok=True, ignore=_copy_ignore)
            elif child.is_file():
                shutil.copy2(child, dest_child)
        problem = _verify_copy(source, target)
        if problem:
            raise ValueError(problem)
    except Exception:
        if owned and target.exists():
            shutil.rmtree(target, ignore_errors=True)
        raise

    pointer = location_file()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(str(target.resolve()), encoding="utf-8")
    pending = pending_delete_file()
    pending.write_text(str(source), encoding="utf-8")
    # The running process still has the old file open until dispose.
    _release_handles()
    _empty_except_pointers(source)
    if _old_settled(source):
        pending.unlink(missing_ok=True)
    return {"path": str(target.resolve()), "moved": True}


def _release_handles() -> None:
    """Drop pooled connections so Windows will allow the old database to be renamed."""
    from app.db import engine

    engine.dispose()


def _empty_except_pointers(root: Path) -> None:
    """Delete every file in the old folder except root-level pointer files."""
    if not root.is_dir():
        return
    entries = list(root.rglob("*"))
    files = [path for path in entries if path.is_file()]
    folders = [path for path in entries if path.is_dir()]
    for path in sorted(files, key=lambda item: len(item.parts), reverse=True):
        if _pointer(path, root):
            continue
        try:
            path.unlink()
        except OSError:
            pass
    for path in sorted(folders, key=lambda item: len(item.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def _old_settled(folder: Path) -> bool:
    """True when the old folder is gone, or only pointer files remain."""
    if not folder.exists():
        return True
    for path in folder.rglob("*"):
        if path.is_file() and not _pointer(path, folder):
            return False
    return True


def _new_db_ok() -> bool:
    if not DATABASE_PATH.is_file():
        return False
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error:
        return False
    finally:
        connection.close()
    return bool(row and row[0] == "ok")


def consume_pending_delete() -> None:
    """Finish a previous move by emptying the old folder down to pointer files.

    If a database file is still locked, the pending file remains.
    """
    pending = pending_delete_file()
    try:
        raw = pending.read_text(encoding="utf-8").strip()
    except OSError:
        return
    if not raw:
        return
    old = Path(raw)
    try:
        same = old.resolve() == DATA_DIR.resolve()
        nested = _nested(old, DATA_DIR) or _nested(DATA_DIR, old)
    except OSError:
        return
    if same or nested or not _new_db_ok():
        return
    if not old.exists():
        pending.unlink(missing_ok=True)
        return
    _empty_except_pointers(old)
    if _old_settled(old):
        pending.unlink(missing_ok=True)
