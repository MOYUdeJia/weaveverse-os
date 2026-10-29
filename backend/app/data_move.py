"""Move the data folder without discarding anything that was not copied.

The location pointer lives outside the data folder. A failed copy never writes
the pointer. After a good copy, only files that exist in the new folder are
removed from the old one. Skipped folders such as whisper_models stay put.
The old database is renamed to weaveverse.old.db immediately, and deleted on
a later startup once this process is no longer holding it.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.config import DATA_DIR, DATABASE_PATH, default_data_dir, location_file, pending_delete_file


SKIP_NAMES = {".weaveverse-port", "_backup_snapshot.db"}
SKIP_SUFFIXES = {".db-wal", ".db-shm"}
SKIP_DIRS = {"whisper_models"}
LIVE_DB = "weaveverse.db"
RETIRED_DB = "weaveverse.old.db"
# Never delete these by the "already copied" pass. The live file is renamed;
# the retired file is removed only on a later startup.
KEPT_DB_NAMES = {LIVE_DB, RETIRED_DB}


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


def _skipped(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in SKIP_DIRS for part in relative.parts):
        return True
    if path.name in SKIP_NAMES or path.name.endswith(".pre-m5.db"):
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in SKIP_DIRS or name in SKIP_NAMES or name.endswith(".pre-m5.db"):
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
    pending_delete_file().write_text(str(source), encoding="utf-8")
    # The running process still has the old file open until dispose.
    _release_handles()
    _retire_database(source)
    _delete_copied(source, target.resolve())
    _prune_empty_dirs(source)
    return {"path": str(target.resolve()), "moved": True}


def _release_handles() -> None:
    """Drop pooled connections so Windows will allow the old database to be renamed."""
    from app.db import engine

    engine.dispose()


def _retire_database(folder: Path) -> bool:
    """Rename weaveverse.db so the old folder no longer shows the live database name."""
    live = folder / LIVE_DB
    retired = folder / RETIRED_DB
    if not live.exists():
        return True
    if retired.exists():
        try:
            retired.unlink()
        except OSError:
            return False
    try:
        live.replace(retired)
    except OSError:
        return False
    for name in ("weaveverse.db-wal", "weaveverse.db-shm"):
        side = folder / name
        try:
            if side.is_file():
                side.unlink()
        except OSError:
            pass
    return True


def _delete_retired_database(folder: Path) -> bool:
    """Remove the renamed database. False means a later startup should try again."""
    ok = True
    for name in (
        RETIRED_DB,
        "weaveverse.old.db-wal",
        "weaveverse.old.db-shm",
        "weaveverse.db-wal",
        "weaveverse.db-shm",
    ):
        path = folder / name
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError:
            ok = False
    if (folder / LIVE_DB).exists():
        return False
    return ok


def _delete_copied(old: Path, new: Path) -> None:
    """Delete only files that were copied. Skipped paths and the database stay."""
    if not old.is_dir() or not new.is_dir():
        return
    files = [path for path in old.rglob("*") if path.is_file()]
    for path in sorted(files, key=lambda item: len(item.parts), reverse=True):
        if _skipped(path, old) or path.name in KEPT_DB_NAMES:
            continue
        dest = new / path.relative_to(old)
        try:
            same_size = dest.is_file() and dest.stat().st_size == path.stat().st_size
        except OSError:
            continue
        if not same_size:
            continue
        try:
            path.unlink()
        except OSError:
            pass


def _prune_empty_dirs(root: Path) -> None:
    if not root.is_dir():
        return
    dirs = [path for path in root.rglob("*") if path.is_dir()]
    for path in sorted(dirs, key=lambda item: len(item.parts), reverse=True):
        if _skipped(path, root):
            continue
        try:
            path.rmdir()
        except OSError:
            pass
    try:
        if root.is_dir() and not any(root.iterdir()):
            root.rmdir()
    except OSError:
        pass


def _old_settled(folder: Path) -> bool:
    """True when the old folder is gone, or only skipped files remain."""
    if not folder.exists():
        return True
    if (folder / LIVE_DB).exists() or (folder / RETIRED_DB).exists():
        return False
    for path in folder.rglob("*"):
        if path.is_file() and not _skipped(path, folder):
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
    """Finish the previous move: rename any leftover database, then delete it.

    Copied files go away. whisper_models and other skipped paths stay.
    If the renamed database is still locked, the pending file remains.
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
    _retire_database(old)
    _delete_retired_database(old)
    _delete_copied(old, DATA_DIR)
    _prune_empty_dirs(old)
    if _old_settled(old):
        pending.unlink(missing_ok=True)
