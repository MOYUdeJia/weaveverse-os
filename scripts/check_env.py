"""Write docs/REPORT.md. Called by scripts/verify.ps1, and safe to run directly."""

from __future__ import annotations

import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
REPORT = ROOT / "docs" / "REPORT.md"


def head_revision() -> str:
    revisions: list[str] = []
    downs: set[str] = set()
    for path in (BACKEND / "alembic" / "versions").glob("*.py"):
        revision = ""
        down = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("revision:"):
                revision = line.split("=", 1)[1].strip().strip("\"'")
            elif line.startswith("down_revision:"):
                down = line.split("=", 1)[1].strip().strip("\"'")
        if revision:
            revisions.append(revision)
            if down and down not in {"None", ""}:
                downs.add(down)
    heads = [item for item in revisions if item not in downs]
    return ",".join(heads)


def database_path() -> Path:
    pointer = BACKEND / ".data-location"
    db = BACKEND / "data" / "weaveverse.db"
    if pointer.is_file():
        chosen = Path(pointer.read_text(encoding="utf-8").strip())
        if chosen.is_dir():
            db = chosen / "weaveverse.db"
    return db


def database_revision(db: Path) -> str:
    if not db.is_file():
        return ""
    connection = sqlite3.connect(db)
    try:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    finally:
        connection.close()
    return row[0] if row else ""


def api_text(port: int, path: str) -> str:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as response:
            return response.read().decode("utf-8")
    except Exception:
        return ""


def main() -> int:
    failed = False
    lines = ["# Weaveverse 环境检查", "", f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    dist = FRONTEND / "dist" / "index.html"
    if dist.is_file():
        dist_time = datetime.fromtimestamp(dist.stat().st_mtime)
        newest = max((path for path in (FRONTEND / "src").rglob("*") if path.is_file()), key=lambda item: item.stat().st_mtime, default=None)
        lines.append(f"- 前端 dist：存在，{dist_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if newest and newest.stat().st_mtime > dist.stat().st_mtime:
            failed = True
            lines.append(f"- 前端是否最新：否。{newest.relative_to(ROOT)} 比 dist 新。")
        else:
            lines.append("- 前端是否最新：是。src 里没有比 dist 更新的文件。")
    else:
        failed = True
        lines.append("- 前端 dist：不存在。请在 frontend 目录执行 npm run build。")

    port = 8765
    port_file = BACKEND / ".weaveverse-port"
    if port_file.is_file():
        raw = port_file.read_text(encoding="utf-8").strip()
        if raw.isdigit():
            port = int(raw)
    health = api_text(port, "/api/health")
    if '"ok"' in health or "ok" in health:
        lines.append(f"- 后端 API：存活（http://127.0.0.1:{port}/api/health）")
    else:
        failed = True
        lines.append(f"- 后端 API：没有响应（http://127.0.0.1:{port}/api/health）。请先启动 backend。")
    status = api_text(port, "/api/system/status")
    lines.append(f"- 运行中的状态接口：{status or '没有返回'}")

    db = database_path()
    current = database_revision(db)
    head = head_revision()
    lines.append(f"- 数据库文件：{db}")
    lines.append(f"- 库里的迁移：{current or '没有读到'}")
    lines.append(f"- 代码里的最新迁移：{head}")
    if not current or current not in head.split(","):
        failed = True
        lines.append("- 数据库是否最新：否。")
    else:
        lines.append("- 数据库是否最新：是。")
    lines.append("")
    lines.append("结论：有项目没有通过。" if failed else "结论：通过。")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
