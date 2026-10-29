"""Move the data folder without deleting the original until the new copy checks out.

The location pointer lives outside the data folder. The old folder is only
removed on the next startup, after the new database opens and passes
integrity_check. A failed copy never writes the pointer.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.config import DATA_DIR, DATABASE_PATH, default_data_dir, location_file, pending_delete_file


SKIP_NAMES = {".weaveverse-port", "_backup_snapshot.db"}
SKIP_SUFFIXES = {".db-wal", ".db-shm"}


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


def _manifest(root: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    if not root.exists():
        return rows
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in SKIP_NAMES or path.suffix.lower() in SKIP_SUFFIXES:
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
            if child.name in SKIP_NAMES:
                continue
            dest_child = target / child.name
            if child.is_dir():
                shutil.copytree(child, dest_child, dirs_exist_ok=True)
            elif child.is_file() and child.suffix.lower() not in SKIP_SUFFIXES:
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
    return {"path": str(target.resolve()), "moved": True}


def consume_pending_delete() -> None:
    """Delete the previous data folder only after this process is using the new one."""
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
    if same or nested or not DATABASE_PATH.is_file():
        return
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error:
        return
    finally:
        connection.close()
    if not row or row[0] != "ok":
        return
    try:
        shutil.rmtree(old)
    except OSError:
        return
    pending.unlink(missing_ok=True)
