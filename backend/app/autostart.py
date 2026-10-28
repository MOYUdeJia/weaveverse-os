"""Windows logon startup via the current-user Run key.

The registry value is the source of truth. A shortcut in the Startup folder
needs a COM call and breaks when the folder is redirected, so this uses HKCU.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "WeaveverseOS"


def _packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def launch_command() -> str:
    """Command line written to Run. Packaged builds use the exe; dev uses pythonw plus main.py."""
    if _packaged():
        return f'"{Path(sys.executable).resolve()}"'
    python = Path(sys.executable).resolve()
    pythonw = python.with_name("pythonw.exe")
    executable = pythonw if pythonw.is_file() else python
    main = Path(__file__).resolve().parents[1] / "main.py"
    return f'"{executable}" "{main}"'


def autostart_enabled() -> bool:
    if os.name != "nt":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_PATH) as key:
            value, _kind = winreg.QueryValueEx(key, RUN_NAME)
    except FileNotFoundError:
        return False
    except OSError:
        return False
    return bool(str(value or "").strip())


def set_autostart(enabled: bool) -> bool:
    if os.name != "nt":
        raise ValueError("开机自启目前只支持 Windows")
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_PATH) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass
    return autostart_enabled()
