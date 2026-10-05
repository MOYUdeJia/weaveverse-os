"""Desktop entry point for Weaveverse OS.

Starts the FastAPI server in a worker thread, then opens the pywebview window on
the main thread so GUI frameworks keep their expected threading model.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
import webview

from app.config import DEV_SERVER_URL, HOST, MIN_HEIGHT, MIN_WIDTH, PORT_FILE, is_dev_mode
from app.static import create_app


server_port: int | None = None
server: uvicorn.Server | None = None


def _can_bind(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, port))
        except OSError:
            return False
    return True


def choose_port(preferred: int = 8765) -> int:
    """Return the preferred local port, or ask the OS for a free fallback."""
    if _can_bind(preferred):
        return preferred

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def write_port_file(port: int) -> None:
    """Share the backend port with Vite when development mode uses a fallback."""
    PORT_FILE.write_text(str(port), encoding="utf-8")


def remove_port_file() -> None:
    try:
        PORT_FILE.unlink()
    except FileNotFoundError:
        pass


def run_server(port: int) -> None:
    global server

    app = create_app()
    config = uvicorn.Config(app, host=HOST, port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()


def wait_until_ready(port: int, timeout_seconds: float = 8.0) -> None:
    """Wait briefly for uvicorn to accept TCP connections before opening UI."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Backend did not become ready on {HOST}:{port}")


def wait_until_url_accepts_connections(url: str, timeout_seconds: float = 120.0) -> None:
    """Wait for the Vite dev server before opening the desktop window."""
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


def shutdown_backend() -> None:
    if server is not None:
        server.should_exit = True


def main() -> None:
    global server_port

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
