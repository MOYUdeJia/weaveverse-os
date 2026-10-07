# Weaveverse Data

M1 stores the local SQLite database at `backend/data/weaveverse.db`.
M2 stores uploaded images at `backend/data/attachments/`.

## Backup

Close Weaveverse OS, then copy `weaveverse.db` and the `attachments/` folder together.

## Restore

Close Weaveverse OS, replace `backend/data/weaveverse.db` and restore `attachments/`, then start the app again.

## Attachments

Gallery uploads are stored as UUID filenames. Deleting a gallery image from the UI also deletes the file.

## Later Versions

The database currently lives inside the project for easier debugging and backups. A later version may move it to a user data directory such as `%APPDATA%`.
