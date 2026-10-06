# Weaveverse OS

Weaveverse OS is a local-first personal digital space for weaving growth, interests, knowledge, inspiration, and memory into one evolving desktop universe.

M1 stores sidebar navigation in a local SQLite database and keeps schema changes under Alembic migrations.

## Requirements

- Python 3.11+
- Node.js 18+
- npm

## Install

Backend:

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

## Production Mode

```bash
cd frontend
npm run build

cd ../backend
python main.py
```

The desktop shell starts FastAPI in a background thread and opens a pywebview window against the local app.
Startup runs Alembic migrations before the server opens, then seeds the original six navigation items only when the database file is first created.

## Development Mode

Terminal 1:

```bash
cd backend
WEAVEVERSE_DEV=1 python main.py
```

Terminal 2:

```bash
cd frontend
npm run dev
```

In development, pywebview loads the Vite dev server at `http://127.0.0.1:5173`. Vite proxies `/api` to the backend port from `WEAVEVERSE_API_PORT`, or from `backend/.weaveverse-port` when available.

When `WEAVEVERSE_DEV=1` is enabled, the backend waits for the Vite dev server before opening the desktop window.

## Structure

```text
backend/
  main.py              # Starts uvicorn in a child thread and pywebview on the main thread
  alembic.ini          # Alembic migration configuration
  alembic/             # Migration environment and versions
  data/                # Local SQLite database folder
  app/
    api.py             # /api/health and /api/nav
    config.py          # Paths, ports, and environment settings
    db.py              # SQLModel engine and request sessions
    models.py          # SQLModel database models
    crud.py            # Database operations
    seed.py            # First-run seed data
    routes/            # API route modules
    static.py          # Production static files and SPA fallback
frontend/
  src/
    api/client.js      # Fetch client for /api navigation CRUD
    components/        # Splash, sidebar, and workspace components
    assets/splash/     # Replaceable splash image
docs/
  M0-TASK.md
  VERSIONS.md
```

## Data

The M1 database lives at `backend/data/weaveverse.db`. To back it up, close the app and copy that `.db` file. To restore it, replace the file and restart Weaveverse OS.
