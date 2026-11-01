"""Desktop entry point for Weaveverse OS.

Starts the FastAPI server in a worker thread, then opens the pywebview window on
the main thread so GUI frameworks keep their expected threading model.
"""

from __future__ import annotations

import ctypes
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
from app.config import BACKEND_DIR, DATABASE_PATH, DATA_DIR, DEV_SERVER_URL, FRONTEND_DIST, HOST, MIN_HEIGHT, MIN_WIDTH, PORT_FILE, PROJECT_ROOT, WINDOW_HOST, is_dev_mode
from app.data_move import consume_pending_delete
from app.db import engine
from app.plugins import ensure_seed
from app.seed import seed_initial_nav_items
from app.timeline import ensure_timeline_page
from app.static import create_app


server_port: int | None = None
server: uvicorn.Server | None = None
_target_url = ""
_PET_SIZE = 132
_PEEK = 18


class DesktopBridge:
    """JavaScript bridge for the system browser, book file dialog, and PDF opener."""

    def __init__(self) -> None:
        self._picked_book: Path | None = None
        self._pet = None
        self._dock: dict | None = None
        self._full = False
        self._before_full: tuple | None = None
        self._zoomed = False
        self._opening = False
        self._pet_shown = False
        self._pet_home = (80, 80)
        self._pet_dragging = False
        self._move_lock = threading.Lock()
        self._move_target: tuple[int, int] | None = None
        self._move_busy = False

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
        window = self._main_window()
        if window is not None:
            window.destroy()
        return True

    def _main_window(self):
        for window in webview.windows:
            if getattr(window, "uid", "") == "master":
                return window
        for window in webview.windows:
            if window is not self._pet:
                return window
        return None

    # 无边框主窗口的最小化、最大化、关闭。
    def window_minimize(self) -> bool:
        window = self._main_window()
        if window is None:
            return False
        window.minimize()
        return True

    def window_maximize(self) -> bool:
        window = self._main_window()
        if window is None:
            return False
        if self._zoomed:
            window.restore()
            self._zoomed = False
        else:
            window.maximize()
            self._zoomed = True
        return True

    def window_close(self) -> bool:
        window = self._main_window()
        if window is None:
            return False
        window.destroy()
        return True

    def _living_pet(self):
        pet = self._pet
        if pet is None:
            return None
        if pet not in webview.windows:
            self._pet = None
            self._dock = None
            self._full = False
            return None
        return pet

    def _forget_pet(self, *_args) -> None:
        self._pet = None
        self._dock = None
        self._full = False
        self._before_full = None
        self._pet_shown = False

    def _screen_for(self, x: int, y: int):
        try:
            screens = list(webview.screens or [])
        except Exception:
            return None
        if not screens:
            return None
        for screen in screens:
            if screen.x <= x < screen.x + screen.width and screen.y <= y < screen.y + screen.height:
                return screen
        return screens[0]

    def _defer(self, fn, delay: float = 0.04) -> None:
        """Run a window call after the JS bridge has returned.

        pywebview delivers js_api on the GUI thread and waits for the return
        value. move, resize, show and create_window also need that thread.
        Doing them inline deadlocks the pet the moment it is clicked.
        """

        def _run() -> None:
            time.sleep(delay)
            try:
                fn()
            except Exception:
                return

        threading.Thread(target=_run, daemon=True).start()

    def _glide(self, pet, x: int, y: int) -> None:
        x0, y0 = pet.x, pet.y
        steps = 8
        for step in range(1, steps + 1):
            t = step / steps
            ease = t * t * (3 - 2 * t)
            try:
                pet.move(round(x0 + (x - x0) * ease), round(y0 + (y - y0) * ease))
            except Exception:
                return
            time.sleep(0.016)

    def _spawn_pet(self) -> None:
        if self._living_pet() is not None:
            return
        base = _target_url or f"http://{WINDOW_HOST}:{server_port or 8765}"
        join = "&" if "?" in base else "?"
        url = f"{base}{join}surface=pet"
        self._pet_shown = False
        self._pet = webview.create_window(
            "专注",
            url,
            width=_PET_SIZE,
            height=_PET_SIZE,
            frameless=True,
            transparent=False,
            on_top=True,
            easy_drag=False,
            shadow=False,
            hidden=True,
            resizable=False,
            text_select=False,
            background_color="#010001",
            min_size=(_PET_SIZE, _PET_SIZE),
            js_api=self,
        )
        if self._pet is not None:
            self._pet.events.closed += self._forget_pet
            threading.Timer(0.6, self._arm_pet_chrome).start()

    # 打开置顶的专注小窗。已打开时只把它显示出来。
    def open_focus_pet(self) -> dict:
        pet = self._living_pet()
        if pet is not None:
            _begin_gui(pet, lambda: pet.show())
            return {"opened": True, "existing": True}
        if self._opening:
            return {"opened": True, "existing": True}
        self._opening = True

        def _open() -> None:
            try:
                self._spawn_pet()
            finally:
                self._opening = False

        self._defer(_open)
        return {"opened": True, "existing": False}

    def focus_geometry(self) -> dict:
        pet = self._living_pet()
        if pet is None:
            return {"ok": False}
        return {"ok": True, "x": pet.x, "y": pet.y, "width": pet.width, "height": pet.height, "full": self._full}

    def focus_nudge(self, dx: int, dy: int) -> dict:
        """Move by a mouse delta. pywebview's own move() truncates the window handle."""
        try:
            step = (int(dx), int(dy))
        except (TypeError, ValueError):
            return {"ok": False}
        if step == (0, 0):
            return {"ok": True}
        pet = self._living_pet()
        if pet is None or self._full:
            return {"ok": False}

        def _go() -> None:
            current = self._living_pet()
            native = getattr(current, "native", None) if current else None
            if native is None:
                return
            scale = float(getattr(native, "_scale", 1) or 1)
            hwnd = _hwnd_of(current)
            if not hwnd:
                return
            _set_window_pos(
                hwnd,
                int(native.Left + step[0] * scale),
                int(native.Top + step[1] * scale),
                0,
                0,
                0x0001 | 0x0004 | 0x0010,
            )

        _begin_gui(pet, _go)
        return {"ok": True}

    def focus_begin_drag(self) -> dict:
        """Track the physical mouse outside WebView2 until the button is released."""
        pet = self._living_pet()
        if pet is None or self._full or self._pet_dragging:
            return {"ok": False}
        hwnd = _hwnd_of(pet)
        if not hwnd:
            return {"ok": False}
        self._pet_dragging = True

        def _drag() -> None:
            class Point(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class Rect(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            cursor = Point()
            rect = Rect()
            try:
                if not user32.GetCursorPos(ctypes.byref(cursor)):
                    return
                if not user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
                    return
                start_mouse = (int(cursor.x), int(cursor.y))
                start_window = (int(rect.left), int(rect.top))
                while user32.GetAsyncKeyState(0x01) & 0x8000:
                    if user32.GetCursorPos(ctypes.byref(cursor)):
                        _set_window_pos(
                            hwnd,
                            start_window[0] + int(cursor.x) - start_mouse[0],
                            start_window[1] + int(cursor.y) - start_mouse[1],
                            0,
                            0,
                            0x0001 | 0x0004 | 0x0010,
                        )
                    time.sleep(0.008)
            finally:
                self._pet_dragging = False

        threading.Thread(target=_drag, daemon=True).start()
        return {"ok": True}

    def focus_move(self, x: int, y: int) -> dict:
        try:
            point = (int(x), int(y))
        except (TypeError, ValueError):
            return {"ok": False}
        pet = self._living_pet()
        if pet is None or self._full:
            return {"ok": False}

        def _go() -> None:
            current = self._living_pet()
            native = getattr(current, "native", None) if current else None
            if native is None:
                return
            scale = float(getattr(native, "_scale", 1) or 1)
            hwnd = _hwnd_of(current)
            if not hwnd:
                return
            _set_window_pos(hwnd, int(point[0] * scale), int(point[1] * scale), 0, 0, 0x0001 | 0x0004 | 0x0010)

        _begin_gui(pet, _go)
        return {"ok": True, "x": point[0], "y": point[1]}

    def focus_resize(self, width: int, height: int) -> dict:
        try:
            size = (max(_PET_SIZE, int(width)), max(_PET_SIZE, int(height)))
        except (TypeError, ValueError):
            return {"ok": False}
        pet = self._living_pet()
        if pet is None or self._full:
            return {"ok": False}

        def _go() -> None:
            current = self._living_pet()
            native = getattr(current, "native", None) if current else None
            if native is None:
                return
            scale = float(getattr(native, "_scale", 1) or 1)
            hwnd = _hwnd_of(current)
            if not hwnd:
                return
            target_width = int(size[0] * scale)
            target_height = int(size[1] * scale)
            x = int(native.Left)
            y = int(native.Top)
            try:
                from System.Windows.Forms import Screen

                area = Screen.FromPoint(native.Location).WorkingArea
                x = min(max(x, int(area.Left)), int(area.Right) - target_width)
                y = min(max(y, int(area.Top)), int(area.Bottom) - target_height)
            except Exception:
                pass
            _set_window_pos(
                hwnd,
                x,
                y,
                target_width,
                target_height,
                0x0004 | 0x0010,
            )
            _finish_pet_chrome(current)

        _begin_gui(pet, _go)
        return {"ok": True, "width": size[0], "height": size[1]}

    def _dock_points(self, pet, screen, side: str) -> dict:
        width = pet.width or _PET_SIZE
        height = pet.height or _PET_SIZE
        y = min(max(pet.y, screen.y), screen.y + screen.height - _PEEK)
        x = min(max(pet.x, screen.x), screen.x + screen.width - _PEEK)
        if side == "left":
            home = (screen.x - width + _PEEK, y)
            shown = (screen.x, y)
        elif side == "right":
            home = (screen.x + screen.width - _PEEK, y)
            shown = (screen.x + screen.width - width, y)
        else:
            home = (x, screen.y - height + _PEEK)
            shown = (x, screen.y)
        return {"side": side, "home": home, "shown": shown}

    def focus_settle(self) -> dict:
        """Park the pet halfway off the nearest left, right, or top edge."""
        pet = self._living_pet()
        if pet is None or self._full:
            return {"dock": None}
        width = pet.width or _PET_SIZE
        height = pet.height or _PET_SIZE
        screen = self._screen_for(pet.x + width // 2, pet.y + height // 2)
        if screen is None:
            return {"dock": None}
        margin = 28
        if pet.x <= screen.x + margin:
            side = "left"
        elif pet.x + width >= screen.x + screen.width - margin:
            side = "right"
        elif pet.y <= screen.y + margin:
            side = "top"
        else:
            self._dock = None
            return {"dock": None}
        self._dock = self._dock_points(pet, screen, side)
        home = self._dock["home"]
        self._defer(lambda: self._glide(pet, home[0], home[1]))
        return {"dock": side}

    def focus_peek(self, show: bool) -> dict:
        pet = self._living_pet()
        dock = self._dock
        if pet is None or dock is None or self._full:
            return {"ok": False}
        point = dock["shown"] if show else dock["home"]
        self._defer(lambda: self._glide(pet, point[0], point[1]))
        return {"ok": True, "show": bool(show)}

    def focus_fullscreen(self, enabled: bool) -> dict:
        pet = self._living_pet()
        if pet is None:
            return {"ok": False}
        if enabled:
            if self._full:
                return {"ok": True, "full": True}
            self._before_full = (pet.x, pet.y, pet.width, pet.height, self._dock)
            screen = self._screen_for(pet.x, pet.y)
            self._full = True
            self._dock = None

            def _enter() -> None:
                current = self._living_pet()
                if current is None or screen is None:
                    return
                _clear_pet_region(current)
                current.move(screen.x, screen.y)
                current.resize(screen.width, screen.height)

            self._defer(_enter)
            return {"ok": True, "full": True}
        if not self._full:
            return {"ok": True, "full": False}
        self._full = False
        saved = self._before_full or (80, 80, _PET_SIZE, _PET_SIZE, None)
        x, y, width, height, dock = saved
        self._dock = dock

        def _leave() -> None:
            current = self._living_pet()
            if current is None:
                return
            current.resize(width, height)
            current.move(x, y)
            _shape_pet(current)
            if dock:
                home = dock["home"]
                self._glide(current, home[0], home[1])

        self._defer(_leave)
        return {"ok": True, "full": False}

    def focus_ready(self) -> dict:
        """Style the pet after it is on screen. Never show or Invoke from this call."""
        self._arm_pet_chrome()
        return {"ok": True}

    def _arm_pet_chrome(self) -> None:
        pet = self._living_pet()
        if pet is None or self._pet_shown:
            return
        self._pet_shown = True

        def _present() -> None:
            _finish_pet_chrome(pet, True)
            try:
                pet.native.Show()
                pet.native.Activate()
            except Exception:
                return

        _begin_gui(pet, _present)

    def focus_hide(self) -> bool:
        pet = self._living_pet()
        if pet is None:
            return False

        def _go() -> None:
            current = self._living_pet()
            if current is not None:
                current.hide()
            main = self._main_window()
            if main is None:
                return
            try:
                main.evaluate_js("window.dispatchEvent(new CustomEvent('wv-pet-hidden'))")
            except Exception:
                return

        self._defer(_go)
        return True

    def close_focus_pet(self, *_args) -> None:
        """Destroy the accessory window when the main window is closing."""
        pet = self._living_pet()
        if pet is None:
            return
        native = getattr(pet, "native", None)
        if native is not None:
            try:
                native.Hide()
            except Exception:
                pass
        self._defer(pet.destroy, 0)


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


def _window_icon() -> str | None:
    """Windows window icons are .ico files. The svg is the same Möbius mark."""
    candidates = (
        FRONTEND_DIST / "icon.ico",
        PROJECT_ROOT / "frontend" / "public" / "icon.ico",
    )
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def _paint_pet_hole(window) -> None:
    """Keep the WebView background stable; the Win32 region supplies the shape."""
    native = getattr(window, "native", None)
    if native is None:
        return
    try:
        from System.Drawing import Color

        browser = getattr(native, "browser", None)
        web = getattr(browser, "webview", None) if browser is not None else None
        key = Color.FromArgb(255, 1, 0, 1)
        if web is not None:
            web.DefaultBackgroundColor = key
        native.BackColor = key
    except Exception:
        return


def _hwnd_of(window) -> int | None:
    native = getattr(window, "native", None)
    if native is None:
        return None
    handle = getattr(native, "Handle", None)
    if handle is None:
        return None
    try:
        return int(handle.ToInt64())
    except Exception:
        try:
            return int(handle)
        except Exception:
            return None


def _park_pet(window) -> None:
    """Working-area pixels are already physical. Do not scale them again."""
    native = getattr(window, "native", None)
    hwnd = _hwnd_of(window)
    if native is None or not hwnd:
        return
    try:
        from System.Windows.Forms import Screen

        area = Screen.FromPoint(native.Location).WorkingArea
    except Exception:
        return
    width = int(native.Width or _PET_SIZE)
    height = int(native.Height or _PET_SIZE)
    x = int(area.Right - width - 36)
    y = int(area.Bottom - height - 48)
    if x < area.Left:
        x = int(area.Left + 24)
    if y < area.Top:
        y = int(area.Top + 24)
    _set_window_pos(hwnd, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010)


def _clear_pet_region(window) -> None:
    hwnd = _hwnd_of(window)
    if not hwnd:
        return
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetWindowRgn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    user32.SetWindowRgn.restype = ctypes.c_int
    user32.SetWindowRgn(ctypes.c_void_p(hwnd), None, 1)


def _shape_pet(window) -> None:
    """Give WebView2 an explicit hit-tested silhouette instead of transparency."""
    native = getattr(window, "native", None)
    hwnd = _hwnd_of(window)
    if native is None or not hwnd:
        return
    width = int(native.ClientSize.Width or native.Width or _PET_SIZE)
    height = int(native.ClientSize.Height or native.Height or _PET_SIZE)
    scale = float(getattr(native, "_scale", 1) or 1)
    css_width = round(width / scale)
    css_height = round(height / scale)
    if css_width > 340 or css_height > 260:
        _clear_pet_region(window)
        return

    def px(value: float) -> int:
        return round(value * scale)

    gdi = ctypes.WinDLL("gdi32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi.CreateEllipticRgn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    gdi.CreateEllipticRgn.restype = ctypes.c_void_p
    gdi.CreateRoundRectRgn.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    ]
    gdi.CreateRoundRectRgn.restype = ctypes.c_void_p
    gdi.CombineRgn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    gdi.CombineRgn.restype = ctypes.c_int
    gdi.DeleteObject.argtypes = [ctypes.c_void_p]
    gdi.DeleteObject.restype = ctypes.c_int
    user32.SetWindowRgn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    user32.SetWindowRgn.restype = ctypes.c_int
    fruit = gdi.CreateEllipticRgn(px(17), px(33), px(116), px(122))
    crown = gdi.CreateEllipticRgn(px(34), px(31), px(102), px(58))
    if not fruit or not crown:
        return
    gdi.CombineRgn(fruit, fruit, crown, 2)  # RGN_OR
    gdi.DeleteObject(crown)
    if css_width > _PET_SIZE + 40:
        menu = gdi.CreateRoundRectRgn(px(140), px(28), px(288), px(193), px(28), px(28))
        if menu:
            gdi.CombineRgn(fruit, fruit, menu, 2)
            gdi.DeleteObject(menu)
    if not user32.SetWindowRgn(ctypes.c_void_p(hwnd), fruit, 1):
        gdi.DeleteObject(fruit)


def _set_window_pos(hwnd: int, x: int, y: int, width: int, height: int, flags: int) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetWindowPos.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = ctypes.c_int
    user32.SetWindowPos(ctypes.c_void_p(hwnd), None, int(x), int(y), int(width), int(height), int(flags))


def _begin_gui(window, fn) -> None:
    """Queue work on the window thread without waiting. Invoke here deadlocks create_window."""
    native = getattr(window, "native", None)
    if native is None or not hasattr(native, "BeginInvoke"):
        return
    try:
        from System import Action

        native.BeginInvoke(Action(fn))
    except Exception:
        return


def _finish_pet_chrome(window, park: bool = False) -> None:
    """Apply the pet's native silhouette and accessory-window behavior."""
    native = getattr(window, "native", None)
    if native is None:
        return
    _paint_pet_hole(window)
    _shape_pet(window)
    _style_pet(window)
    if park:
        _park_pet(window)


def _style_pet(window) -> None:
    """Drop the taskbar button and the native square shadow. Not on the show path."""
    if sys.platform != "win32":
        return
    hwnd = _hwnd_of(window)
    if not hwnd:
        return
    try:
        _force_toolwindow(hwnd)
        _disable_dwm_shadow(hwnd)
    except Exception:
        return


def _force_toolwindow(hwnd: int) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gwl_exstyle = -20
    toolwindow = 0x00000080
    appwindow = 0x00040000
    pointer = ctypes.c_void_p(hwnd)
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        get_long = user32.GetWindowLongPtrW
        set_long = user32.SetWindowLongPtrW
        get_long.restype = ctypes.c_ssize_t
        set_long.restype = ctypes.c_ssize_t
        get_long.argtypes = [ctypes.c_void_p, ctypes.c_int]
        set_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
    else:
        get_long = user32.GetWindowLongW
        set_long = user32.SetWindowLongW
        get_long.restype = ctypes.c_long
        set_long.restype = ctypes.c_long
        get_long.argtypes = [ctypes.c_void_p, ctypes.c_int]
        set_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
    style = get_long(pointer, gwl_exstyle)
    if not style:
        return
    updated = (style | toolwindow) & ~appwindow
    if updated != style:
        set_long(pointer, gwl_exstyle, updated)
    _set_window_pos(hwnd, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0010 | 0x0020)


def _disable_dwm_shadow(hwnd: int) -> None:
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
    policy = ctypes.c_int(1)
    dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 2, ctypes.byref(policy), ctypes.sizeof(policy))


# 迁移、种数据、起服务、打开桌面窗口。
# Migrate, seed, start the server, and open the desktop window.
def _open_desktop(window, *, holes: bool = False) -> None:
    """Show the desktop through pixels the page leaves unpainted.

    The form is black, and WinForms treats that black as the color key.
    Do this only after the page has loaded, and do not call SetWindowLong
    from the show path. That call runs inside the window procedure, leaves
    the transparent window hidden, and the process sits on the server log
    with no window. ``holes`` keeps the tomato and the main window on one path.
    background_color stays a 6-digit hex.
    """

    del holes

    def apply(*_args) -> None:
        native = getattr(window, "native", None)
        if native is None:
            return
        try:
            from System.Drawing import Color

            browser = getattr(native, "browser", None)
            web = getattr(browser, "webview", None) if browser is not None else None
            if web is not None:
                web.DefaultBackgroundColor = Color.Transparent
            native.BackColor = Color.Black
            native.TransparencyKey = Color.Black
        except Exception:
            return

    try:
        window.events.loaded += apply
    except Exception:
        return


def main() -> None:
    global server_port, _target_url

    if getattr(sys, "frozen", False):
        os.chdir(Path(sys._MEIPASS))

    database_existed = run_migrations()
    consume_pending_delete()
    seed_initial_nav_items(should_seed=not database_existed)
    ensure_seed()
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

    icon = _window_icon()
    _target_url = target_url
    bridge = DesktopBridge()
    window = webview.create_window(
        "Weaveverse OS",
        target_url,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        width=1180,
        height=760,
        text_select=True,
        js_api=bridge,
    )
    window.events.closing += bridge.close_focus_pet
    window.events.closed += shutdown_backend

    try:
        webview.start(icon=icon)
    finally:
        shutdown_backend()
        thread.join(timeout=5)
        remove_port_file()


if __name__ == "__main__":
    main()
