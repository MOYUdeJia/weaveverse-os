# Weaveverse OS

Weaveverse OS is a local-first personal digital space for weaving growth, interests, knowledge, inspiration, and memory into one evolving desktop universe.

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
  app/
    api.py             # /api/health and /api/nav
    config.py          # Paths, ports, and environment settings
    static.py          # Production static files and SPA fallback
frontend/
  src/
    api/client.js      # Fetch client for /api
    components/        # Splash, sidebar, and workspace components
    assets/splash/     # Replaceable splash image
docs/
  M0-TASK.md
  VERSIONS.md
```
