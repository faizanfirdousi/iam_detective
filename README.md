# IAM Detective
An interactive investigation web app where the player becomes a detective: you open a case file, build an evidence board, interrogate people, spot contradictions, and submit a final theory for scoring.

This repo contains:
- A **Next.js** frontend (the “investigation workspace” UI: pinboard, chat, timeline, notes, conclusion).
- A **FastAPI** backend (case archive + session engine + persistence + LLM-powered narrative and assistants).

## The Big Idea (How the app feels)
IAM Detective is designed to feel less like a website and more like a **digital case file**:
- You pick a real-world case from an archive.
- You get a cinematic introduction to set the tone (time, place, discovery, mystery).
- You investigate in **stages** (crime scene → forensics → witnesses → suspects → build the case → verdict). Each stage unlocks more information.
- You work inside a “workspace”:
  - A **pinboard graph** (nodes/edges you can move around, persisted per session).
  - A **chat** with role-play personas (co-detective / witness / suspect) that respects stage boundaries.
  - A **timeline** of what happened (and what you discovered).
  - A **final conclusion** submission that gets evaluated for accuracy and reasoning.

## Tech Overview
- **Frontend:** Next.js (App Router) + React + TypeScript + Tailwind + React Flow (pinboard graph).
- **Backend:** FastAPI + Pydantic + async SQLAlchemy.
- **Storage:** SQLite by default (local dev), Postgres supported (Docker or managed DB).
- **AI:** Uses a DigitalOcean “AI Agent” style endpoint (OpenAI-compatible-ish) for:
  - case intro + slides
  - persona chat
  - graph extraction/enrichment

## Repository Layout
- `frontend/` — Next.js app
- `backend/` — FastAPI app, investigation engine, DB models
- `docs/` — additional setup notes (e.g. Postgres)
- `prd.md` — product vision + user flow

## Quickstart (Local Dev)

### 1) Backend (FastAPI)
The backend runs on `http://localhost:8000` by default.

Prereqs:
- Python 3.12+ recommended

Setup:
```bash
cd backend
python -m venv .venv
```

Activate the venv:
- Windows (PowerShell):
  ```bash
  .\.venv\Scripts\Activate.ps1
  ```
- macOS/Linux:
  ```bash
  source .venv/bin/activate
  ```

Install dependencies and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:
- `GET http://localhost:8000/health`

### 2) Frontend (Next.js)
The frontend runs on `http://localhost:3000`.

Prereqs:
- Node.js 18+ recommended

Setup:
```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api/*` to the backend in development (see `frontend/next.config.ts`).

## Environment Variables

### Backend
Create a `.env` file in the repo root or inside `backend/` (the backend loads env vars on startup).

**Database**
- `DATABASE_URL` (optional): defaults to SQLite at `sqlite+aiosqlite:///./iam_detective.db` (stored in `backend/`).
- `DB_SSL` (optional): `auto` (default) | `require` | `disable`

Example (local Postgres):
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/iam_detective
DB_SSL=disable
```

**CORS (frontend origin)**
- `CORS_ORIGINS` (optional): comma-separated list. Defaults to `http://localhost:3000`.

**AI Agent (required for the “full experience”)**
Many endpoints (case intro, slides, persona chat, graph building) require an agent endpoint + access key.

Generic config:
- `DO_AGENT_ENDPOINT`
- `DO_AGENT_ACCESS_KEY`

Optional case-specific overrides (if you want separate agents per case):
- `DO_AGENT_ZODIAC_ENDPOINT` / `DO_AGENT_ZODIAC_ACCESS_KEY`
- `DO_AGENT_OJ_ENDPOINT` / `DO_AGENT_OJ_ACCESS_KEY`
- `DO_AGENT_AARUSHI_ENDPOINT` / `DO_AGENT_AARUSHI_ACCESS_KEY`
- `DO_AGENT_GSK_ENDPOINT` / `DO_AGENT_GSK_ACCESS_KEY`

If these are missing, the backend returns a `503` with a `missing_gradient_agent_config:*` detail for affected endpoints.

### Frontend (optional)
Used mainly for server-side requests (SSR/build time):
- `NEXT_PUBLIC_BACKEND_URL` (e.g. `http://localhost:8000`)
- `APP_URL` (DigitalOcean platforms often inject this automatically)

## Using Postgres (Docker)

### Option A (Recommended for dev): Postgres in Docker, backend locally
Start only the database:
```bash
docker compose up db
```

Then set:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/iam_detective
DB_SSL=disable
```

Run the backend locally on port `8000` as shown above.

### Option B: Postgres + backend in Docker Compose
This brings up:
- Postgres on `localhost:5432`
- Backend on `localhost:8080`

```bash
docker compose up --build
```

Note: the frontend dev proxy points to `http://localhost:8000` by default. If you run the backend on `8080`, update the proxy target (or run the backend locally on `8000`).

## API Notes
- Most “me/session” endpoints require an `x-user-id` header. The frontend generates one and stores it in localStorage.
- Core API base path is `/api` (examples: `/api/cases`, `/api/me/cases`, `/api/sessions/{id}`).

## Smoke Test (Backend)
There is a small smoke test that boots the app and exercises a few endpoints using an isolated SQLite DB:
```bash
cd backend
python smoke_test.py
```

## Where to Look Next
- Product flow and UX goals: `prd.md`
- Backend routes: `backend/app/main.py`
- Investigation engine + scoring: `backend/app/engine/`
- Frontend workspace UI: `frontend/app/case/[id]/workspace/page.tsx`
