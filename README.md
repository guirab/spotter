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

## Checks

```sh
(cd backend && pytest)                              # backend tests
(cd frontend && npm run typecheck && npm run lint)
```
