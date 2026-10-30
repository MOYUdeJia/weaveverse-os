"""Old data directory after a move: only pointer files may remain.

Seam: move_data_dir(). The assertion is the directory on disk, not which
helper deleted a path. Whisper models, safety copies, and pre-m5 backups
are part of that directory and have to go with everything else.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


POINTER_FILE = "location.txt"


def _sqlite_with_nav(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE nav_items (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()


class OldDirectoryClearedTest(unittest.TestCase):
    def test_old_directory_keeps_only_pointer_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old-data"
            new = root / "new-data"
            old.mkdir()
            new.mkdir()
            _sqlite_with_nav(old / "weaveverse.db")
            (old / "attachments").mkdir()
            (old / "attachments" / "note.txt").write_text("keep-in-new", encoding="utf-8")
            model = old / "whisper_models" / "base"
            model.mkdir(parents=True)
            (model / "model.bin").write_bytes(b"cache")
            safety = old / "safety" / "2026-10-30"
            safety.mkdir(parents=True)
            (safety / "weaveverse.db").write_bytes(b"backup")
            (old / "archive.pre-m5.db").write_bytes(b"ancient")
            (old / POINTER_FILE).write_text("keep-me", encoding="utf-8")

            pointer = root / "location-pointer.txt"
            pending = root / ".pending-delete"

            with (
                patch("app.data_move.DATA_DIR", old),
                patch("app.data_move.location_file", lambda: pointer),
                patch("app.data_move.pending_delete_file", lambda: pending),
                patch("app.data_move._checkpoint", lambda: None),
                patch("app.data_move._release_handles", lambda: None),
            ):
                from app.data_move import move_data_dir

                move_data_dir(str(new))

            self.assertTrue((new / "weaveverse.db").is_file())
            self.assertTrue((old / POINTER_FILE).is_file())
            self.assertEqual((old / POINTER_FILE).read_text(encoding="utf-8"), "keep-me")
            leftover = sorted(path.relative_to(old).as_posix() for path in old.rglob("*") if path.is_file())
            self.assertEqual(leftover, [POINTER_FILE])
            self.assertFalse((old / "whisper_models").exists())
            self.assertFalse((old / "safety").exists())
            self.assertFalse(any(path.name.endswith(".pre-m5.db") for path in old.rglob("*")))


if __name__ == "__main__":
    unittest.main()
