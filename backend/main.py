"""Desktop entry point for Weaveverse OS.

Starts the FastAPI server in a worker thread, then opens the pywebview window on
the main thread so GUI frameworks keep their expected threading model.
"""

from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

from alembic import command
from alembic.config import Config
from sqlmodel import Session
import uvicorn
import webview

from app import book_crud
from app.book_files import original_path
from app.config import BACKEND_DIR, DATABASE_PATH, DATA_DIR, DEV_SERVER_URL, HOST, MIN_HEIGHT, MIN_WIDTH, PORT_FILE, is_dev_mode
from app.db import engine
from app.seed import seed_initial_nav_items
from app.static import create_app


server_port: int | None = None
server: uvicorn.Server | None = None


class DesktopBridge:
    """JavaScript bridge for the system browser, book file dialog, and PDF opener."""

    def __init__(self) -> None:
        self._picked_book: Path | None = None

    # 用系统浏览器打开 http(s) 外链。
    # Open an http(s) URL in the system browser.
    def open_url(self, url: str) -> bool:
        if not isinstance(url, str):
            return False
        target = url.strip()
        if not target.startswith(("http://", "https://")):
            return False
        webbrowser.open(target)
        return True

    # 弹出系统文件选择器，只记住路径，不在这里读文件。
    # Open the system file dialog and remember the path without reading it yet.
    def pick_book_file(self) -> dict | None:
        window = webview.windows[0] if webview.windows else None
        if window is None:
            return {"error": "窗口还没准备好"}

        try:
            selected = window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=("电子书 (*.epub;*.txt;*.pdf)",),
            )
        except Exception:
            self._picked_book = None
            return {"error": "无法打开文件选择器"}

        if not selected:
            self._picked_book = None
            return None

        path = Path(selected[0])
        if path.suffix.lower() not in {".epub", ".txt", ".pdf"} or not path.is_file():
            self._picked_book = None
            return {"error": "仅支持 epub / txt / pdf"}

        self._picked_book = path
        return {"name": path.name, "size": path.stat().st_size}

    # 把刚才选中的文件导入书架。上传仍是整文件读入内存。
    # Import the file chosen above. The upload is still fully buffered in memory.
    def import_picked_book(self) -> dict:
        path = self._picked_book
        self._picked_book = None
        if path is None or not path.is_file():
            return {"error": "还没有选择文件"}

        try:
            payload = path.read_bytes()
            with Session(engine) as session:
                book = book_crud.create_book(session, path.name, payload)
                return {"id": book.id}
        except ValueError as exc:
            return {"error": str(exc)}
        except OSError:
            return {"error": "无法读取这个文件"}

    # 用系统默认程序打开 PDF 原件。
    # Open a PDF original in the system default application.
    def open_book(self, book_id: int) -> bool:
        try:
            book_id = int(book_id)
        except (TypeError, ValueError):
            return False

        with Session(engine) as session:
            book = book_crud.get_book(session, book_id)
            if book is None or book.format != "pdf":
                return False
            path = original_path(book.id, book.format)

        if not path.is_file() or os.name != "nt":
            return False
        os.startfile(path)
        return True

    # 用系统默认程序打开一篇长文里的附件。
    # Open one doc attachment in the system default application.
    def open_attachment(self, filename: str) -> bool:
        from app.routes.blocks import _safe_attachment_path

        if not isinstance(filename, str) or os.name != "nt":
            return False
        try:
            path = _safe_attachment_path(filename)
        except Exception:
            return False
        if not path.is_file():
            return False
        os.startfile(path)
        return True


# 探测本机端口是否可绑定。
# Probe whether a local port can be bound.
def _can_bind(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, port))
        except OSError:
            return False
    return True


# 优先使用 8765，占用则让系统分配。
# Prefer port 8765, otherwise ask the OS for a free port.
def choose_port(preferred: int = 8765) -> int:
    if _can_bind(preferred):
        return preferred

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


# 把实际端口写给 Vite 代理读取。
# Share the backend port with the Vite proxy.
def write_port_file(port: int) -> None:
    PORT_FILE.write_text(str(port), encoding="utf-8")


# 退出时删掉端口文件。
# Remove the port file on shutdown.
def remove_port_file() -> None:
    try:
        PORT_FILE.unlink()
    except FileNotFoundError:
        pass


# 在子线程里运行 uvicorn。
# Run uvicorn in a worker thread.
def run_server(port: int) -> None:
    global server

    app = create_app()
    config = uvicorn.Config(app, host=HOST, port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()


# 启动前把 SQLite schema 升到最新 Alembic revision。
# Upgrade the SQLite schema to the latest Alembic revision before serving.
def run_migrations() -> bool:
    database_existed = DATABASE_PATH.exists()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(alembic_config, "head")
    return database_existed


# 等到后端 TCP 端口开始接受连接。
# Wait until the backend TCP port accepts connections.
def wait_until_ready(port: int, timeout_seconds: float = 8.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Backend did not become ready on {HOST}:{port}")


# 开发模式先等 Vite 端口就绪再开窗口。
# Wait for the Vite dev server before opening the desktop window.
def wait_until_url_accepts_connections(url: str, timeout_seconds: float = 120.0) -> None:
    parsed = urlsplit(url)
    host = parsed.hostname or HOST
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.25)

    raise RuntimeError(f"Dev server did not become ready at {url}")


# 通知 uvicorn 退出。
# Ask uvicorn to exit.
def shutdown_backend() -> None:
    if server is not None:
        server.should_exit = True


# 迁移、种数据、起服务、打开桌面窗口。
# Migrate, seed, start the server, and open the desktop window.
def main() -> None:
    global server_port

    database_existed = run_migrations()
    seed_initial_nav_items(should_seed=not database_existed)

    server_port = choose_port()
    write_port_file(server_port)

    thread = threading.Thread(target=run_server, args=(server_port,), daemon=True)
    thread.start()
    wait_until_ready(server_port)

    if is_dev_mode():
        print(f"Waiting for Vite dev server at {DEV_SERVER_URL} ...")
        wait_until_url_accepts_connections(DEV_SERVER_URL)
        target_url = DEV_SERVER_URL
    else:
        target_url = f"http://{HOST}:{server_port}"

    window = webview.create_window(
        "Weaveverse OS",
        target_url,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        width=1180,
        height=760,
        js_api=DesktopBridge(),
    )
    window.events.closed += shutdown_backend

    try:
        webview.start()
    finally:
        shutdown_backend()
        thread.join(timeout=5)
        remove_port_file()


if __name__ == "__main__":
    main()
