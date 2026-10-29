"""Desktop entry point for Weaveverse OS.

Starts the FastAPI server in a worker thread, then opens the pywebview window on
the main thread so GUI frameworks keep their expected threading model.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit


def _use_project_python() -> None:
    """Start with backend/.venv when the shell Python cannot see the project packages."""
    if getattr(sys, "frozen", False):
        return
    venv_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if not venv_python.is_file():
        return
    try:
        if Path(sys.executable).resolve() == venv_python.resolve():
            return
    except OSError:
        return
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


_use_project_python()

from alembic import command
from alembic.config import Config
from sqlmodel import Session
import uvicorn
import webview

from app import book_crud
from app.book_files import original_path
from app.config import BACKEND_DIR, DATABASE_PATH, DATA_DIR, DEV_SERVER_URL, HOST, MIN_HEIGHT, MIN_WIDTH, PORT_FILE, WINDOW_HOST, is_dev_mode
from app.data_move import consume_pending_delete
from app.db import engine
from app.seed import seed_initial_nav_items
from app.timeline import ensure_timeline_page
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

    # 把附件原图另存到用户选的路径，不改库里的文件。
    # Copy an attachment original to a path the user picks. The library file stays.
    def save_attachment(self, filename: str, suggested_name: str = "") -> dict:
        import shutil

        from app.routes.blocks import _safe_attachment_path

        if not isinstance(filename, str):
            return {"error": "非法文件名"}
        try:
            source = _safe_attachment_path(filename)
        except Exception:
            return {"error": "非法文件名"}
        if not source.is_file():
            return {"error": "附件不存在"}

        window = webview.windows[0] if webview.windows else None
        if window is None:
            return {"error": "窗口还没准备好"}

        name = Path(suggested_name or filename).name
        if not name or name in {".", ".."}:
            name = source.name
        try:
            selected = window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=name,
            )
        except Exception:
            return {"error": "无法打开保存对话框"}
        if not selected:
            return None

        target = Path(selected[0] if isinstance(selected, (list, tuple)) else selected)
        try:
            shutil.copy2(source, target)
        except OSError:
            return {"error": "无法保存这个文件"}
        return {"path": str(target)}

    # 把当前主题存到用户选的路径，默认打开主题目录。
    # Save the current theme JSON through the system Save As dialog.
    def save_theme_file(self, content: str, suggested_name: str = "theme.wvtheme") -> dict | None:
        if not isinstance(content, str) or not content.strip() or len(content) > 64 * 1024:
            return {"error": "主题内容无效"}
        folder = DATA_DIR / "themes"
        folder.mkdir(parents=True, exist_ok=True)
        name = Path(suggested_name or "theme.wvtheme").name
        if not name.endswith((".wvtheme", ".json")):
            name = f"{name}.wvtheme"
        window = webview.windows[0] if webview.windows else None
        if window is None:
            return {"error": "窗口还没准备好"}
        try:
            selected = window.create_file_dialog(
                webview.FileDialog.SAVE,
                directory=str(folder),
                save_filename=name,
                file_types=("Weaveverse 主题 (*.wvtheme;*.json)",),
            )
        except Exception:
            return {"error": "无法打开保存对话框"}
        if not selected:
            return None
        target = Path(selected[0] if isinstance(selected, (list, tuple)) else selected)
        if target.suffix.lower() not in {".wvtheme", ".json"}:
            target = target.with_suffix(".wvtheme")
        try:
            target.write_text(content, encoding="utf-8")
        except OSError:
            return {"error": "无法保存主题文件"}
        return {"path": str(target)}

    # 把主题包写到用户选的路径。内容是 base64，避免桥接传二进制。
    # Write a theme pack to the path chosen in the system Save As dialog.
    def save_binary_file(self, content_b64: str, suggested_name: str = "preset.wvpack") -> dict | None:
        import base64

        if not isinstance(content_b64, str) or len(content_b64) > 120_000_000:
            return {"error": "文件太大"}
        try:
            payload = base64.b64decode(content_b64)
        except Exception:
            return {"error": "文件内容无效"}
        folder = DATA_DIR / "themes"
        folder.mkdir(parents=True, exist_ok=True)
        name = Path(suggested_name or "preset.wvpack").name
        if not name.endswith(".wvpack"):
            name = f"{name}.wvpack"
        window = webview.windows[0] if webview.windows else None
        if window is None:
            return {"error": "窗口还没准备好"}
        try:
            selected = window.create_file_dialog(
                webview.FileDialog.SAVE,
                directory=str(folder),
                save_filename=name,
                file_types=("Weaveverse 预设 (*.wvpack)",),
            )
        except Exception:
            return {"error": "无法打开保存对话框"}
        if not selected:
            return None
        target = Path(selected[0] if isinstance(selected, (list, tuple)) else selected)
        if target.suffix.lower() != ".wvpack":
            target = target.with_suffix(".wvpack")
        try:
            target.write_bytes(payload)
        except OSError:
            return {"error": "无法保存文件"}
        return {"path": str(target)}

    # 选择新的数据目录。只返回路径，复制在 HTTP 接口里做。
    # Return a folder path. Copying happens in the data-dir HTTP route.
    def pick_folder(self) -> dict | None:
        window = webview.windows[0] if webview.windows else None
        if window is None:
            return {"error": "窗口还没准备好"}
        folder_mode = getattr(webview.FileDialog, "FOLDER", None)
        if folder_mode is None:
            return {"error": "当前窗口不能选择文件夹"}
        try:
            selected = window.create_file_dialog(folder_mode)
        except Exception:
            return {"error": "无法打开文件夹选择器"}
        if not selected:
            return None
        path = Path(selected[0] if isinstance(selected, (list, tuple)) else selected)
        if not path.is_dir():
            return {"error": "没有选中文件夹"}
        return {"path": str(path)}

    # 用新进程重新打开，让数据目录指针生效。旧窗口随即关闭。
    # Start a new process so the data-dir pointer is read, then close this window.
    def relaunch(self) -> bool:
        import subprocess

        if getattr(sys, "frozen", False):
            command = [sys.executable]
            cwd = None
        else:
            command = [sys.executable, *sys.argv]
            cwd = str(BACKEND_DIR)
        flags = 0
        if os.name == "nt":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(command, cwd=cwd, creationflags=flags, close_fds=True)
        window = webview.windows[0] if webview.windows else None
        if window is not None:
            window.destroy()
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
    log_level = "warning" if getattr(sys, "frozen", False) else "info"
    config = uvicorn.Config(app, host=HOST, port=port, log_level=log_level)
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
            with socket.create_connection((WINDOW_HOST, port), timeout=0.25):
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

    if getattr(sys, "frozen", False):
        os.chdir(Path(sys._MEIPASS))

    database_existed = run_migrations()
    consume_pending_delete()
    seed_initial_nav_items(should_seed=not database_existed)
    with Session(engine) as session:
        ensure_timeline_page(session)

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
        target_url = f"http://{WINDOW_HOST}:{server_port}"

    window = webview.create_window(
        "Weaveverse OS",
        target_url,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        width=1180,
        height=760,
        text_select=True,
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
