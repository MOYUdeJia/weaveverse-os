# Weaveverse Data

M1 stores the local SQLite database at `backend/data/weaveverse.db`.

## Backup

Close Weaveverse OS, then copy `weaveverse.db` to another folder or drive.

## Restore

Close Weaveverse OS, replace `backend/data/weaveverse.db` with your backup copy, then start the app again.

## Later Versions

M1 keeps the database inside the project for easier debugging and backups. A later version may move it to a user data directory such as `%APPDATA%`.
