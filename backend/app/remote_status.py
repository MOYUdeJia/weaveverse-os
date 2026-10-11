"""Read Tailscale status. This module never changes Tailscale settings."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import PORT_FILE


def _binary() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    windows = Path(r"C:\Program Files\Tailscale\tailscale.exe")
    if windows.is_file():
        return str(windows)
    return None


def _port() -> int:
    try:
        return int(PORT_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 8765


def tailscale_status() -> dict:
    binary = _binary()
    port = _port()
    if binary is None:
        return {"state": "missing", "ip": "", "port": port, "url": ""}
    try:
        result = subprocess.run(
            [binary, "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"state": "missing", "ip": "", "port": port, "url": ""}
    ip = ""
    for line in (result.stdout or "").splitlines():
        candidate = line.strip()
        if candidate.startswith("100."):
            ip = candidate
            break
    if result.returncode != 0 or not ip:
        return {"state": "logged_out", "ip": "", "port": port, "url": ""}
    return {"state": "connected", "ip": ip, "port": port, "url": f"http://{ip}:{port}"}
