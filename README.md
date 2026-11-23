# Spotter — Weather-Aware Truck Routing

React + Django app that picks the safest of 3 truck routes based on weather, load weight and travel time. See `PLAN.md` for the design.

## Layout

- `backend/` — Django + DRF API (Python 3.13).
- `frontend/` — Vite + React + TypeScript + Tailwind + TanStack Query + shadcn/ui.

## Local setup

Requirements: Python 3.13 and Node 20.19+ (or 22.12+).

### Backend (http://localhost:8000)

```sh
cd backend
python -m venv .venv
source .venv/bin/activate     # Git Bash: source .venv/Scripts/activate · PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # then fill in TOMTOM_API_KEY
python manage.py runserver
```

`.env.example` lists every variable. `DJANGO_SECRET_KEY` is required unless `DEBUG=True`.

### Frontend (http://localhost:5173)

```sh
cd frontend
npm install
npm run dev
```

In dev, Vite proxies `/api` to `http://localhost:8000`, so no CORS setup is needed. In production, set `VITE_API_BASE_URL` to the backend origin (see `frontend/.env.example`).

Open http://localhost:5173: the page shows **API healthy** when both apps are running.

## Deployment

| App | Host | URL |
|-----|------|-----|
| Frontend | Vercel | _TBD_ |
| Backend | Railway | _TBD_ |

### Backend on Railway

- Root directory: `backend`. Config file path: `/backend/railway.json` (Railway resolves it from the repo root, not the root directory).
- `railway.json` sets the gunicorn start command (it binds to Railway's `$PORT` by default) and the `/api/health` health check.
- Variables:
  - `DJANGO_SECRET_KEY`: a long random string.
  - `DEBUG=False`
  - `ALLOWED_HOSTS=<railway domain>,healthcheck.railway.app` (Railway's health check sends that host).
  - `CORS_ALLOWED_ORIGINS=https://<vercel domain>`: no trailing slash.
  - `TOMTOM_API_KEY`

### Frontend on Vercel

- Root directory: `frontend`. Framework preset: Vite (auto-detected).
- Variable: `VITE_API_BASE_URL=https://<railway domain>` (no trailing slash). It is read at build time, so redeploy after changing it.

The production Vercel URL should show **API healthy** with no CORS errors in the console. Preview deployments get other domains, which are not in `CORS_ALLOWED_ORIGINS`, so they show "API unreachable".

## Checks

```sh
(cd backend && pytest)                              # backend tests
(cd frontend && npm run typecheck && npm run lint)
```
