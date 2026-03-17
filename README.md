# IAM Detective

> **🌊 Built for the DigitalOcean Hackathon** — Entirely powered by DigitalOcean's managed infrastructure: App Platform, Managed Postgres, and AI Agents with Knowledge Bases.

An interactive investigation web app where you become the detective. Open a case file, build an AI-powered evidence board, chat with witnesses and suspects, spot contradictions, and submit your final theory for scoring.

🔗 **Live App:** [https://lionfish-app-swbw4.ondigitalocean.app/](https://lionfish-app-swbw4.ondigitalocean.app/)

---

## 🌊 DigitalOcean — The Backbone of IAM Detective

IAM Detective is built **entirely on DigitalOcean**:

| Layer | DigitalOcean Product |
|---|---|
| Frontend + Backend hosting | **App Platform** (Next.js + FastAPI services) |
| Database | **Managed Postgres** (DO managed DB cluster) |
| AI chat & personas | **AI Agents** (OpenAI-compatible endpoint, no key management) |
| Evidence knowledge base | **Knowledge Bases** (RAG-powered document retrieval) |

The entire AI investigation experience — case intros, witness personas, suspect interrogation, graph enrichment — is powered by **DO AI Agents backed by Knowledge Bases** with zero external API keys required.

---

## 🧠 How the RAG + AI Agent Flow Works

IAM Detective uses DigitalOcean's **Knowledge Base + AI Agent** architecture to power intelligent, evidence-aware conversations.

```
                        ┌─────────────────────────────┐
                        │        User Chat Input        │
                        │  (question to witness/suspect)│
                        └────────────┬────────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────────┐
                        │     FastAPI Backend           │
                        │  - Validates stage/gate       │
                        │  - Injects case context       │
                        │  - Builds system prompt       │
                        └────────────┬────────────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │       DigitalOcean AI Agent               │
              │  - Persona role-play (suspect/witness)    │
              │  - Stage-aware response boundaries        │
              │  - Powered by the Knowledge Base RAG      │
              └────────────┬─────────────────────────────┘
                           │
              ┌────────────▼─────────────────────────────┐
              │       DO Knowledge Base (RAG)             │
              │  - Case documents: police reports,        │
              │    witness statements, forensics, etc.    │
              │  - Chunked & embedded at ingest time      │
              │  - Semantically retrieved per query       │
              └──────────────────────────────────────────┘
                           │
              ┌────────────▼─────────────────────────────┐
              │       AI Agent Response                   │
              │  - Grounds reply in retrieved evidence    │
              │  - Respects persona (e.g. "Arthur: ...")  │
              │  - Detects contradictions vs known facts  │
              └──────────────────────────────────────────┘
                           │
                           ▼
              ┌──────────────────────────────────────────┐
              │    Frontend Updates                       │
              │  - Chat reply displayed                   │
              │  - New evidence nodes unlocked on board   │
              │  - Contradiction toasts surfaced          │
              └──────────────────────────────────────────┘
```

### Knowledge Base — What's in It

Each case has its own DO Knowledge Base populated with:
- **Police reports** and official investigation documents
- **Witness statements** (verbatim transcripts)
- **Forensic reports** and physical evidence descriptions
- **Timeline events**
- **Suspect profiles** and background info

When a user asks "Where were you on the night of the 4th?", the AI Agent retrieves the relevant statement chunks from the Knowledge Base and answers in character — grounded in actual case evidence.

### AI Agent — What It Does

- **Persona chat**: Responds as the chosen witness or suspect using RAG-retrieved context
- **Co-detective assistant**: Acts like a Sherlock-style partner, suggesting connections and highlighting inconsistencies
- **Graph enrichment**: After each investigation stage, the agent extracts entities (persons, locations, evidence) and builds the investigation board automatically
- **Stage gating**: The agent will not reveal information beyond the player's current investigation stage — maintaining narrative tension

---

## The Big Idea

IAM Detective is designed to feel less like a website and more like a **digital case file**:
- You pick a real-world case from an archive
- You get a cinematic introduction to set the tone
- You investigate in **stages** (crime scene → forensics → witnesses → suspects → build the case → verdict)
- You work inside a detective workspace:
  - A **pinboard graph** (AI-generated nodes and connections you can rearrange)
  - A **RAG-powered chat** with role-play personas (co-detective / witness / suspect)
  - A **timeline** of discovered events
  - A **final conclusion** submission that gets evaluated for accuracy and reasoning

---

## Tech Overview

- **Frontend:** Next.js (App Router) + React + TypeScript + Tailwind + React Flow (pinboard graph)
- **Backend:** FastAPI + Pydantic + async SQLAlchemy
- **Storage:** DigitalOcean Managed Postgres (production), SQLite (local dev)
- **AI:** DigitalOcean AI Agents + Knowledge Bases for:
  - Case intro and cinematic slides
  - Persona chat (witness / suspect / co-detective)
  - Graph extraction and enrichment
  - Contradiction detection

## Repository Layout

- `frontend/` — Next.js app
- `backend/` — FastAPI app, investigation engine, DB models
- `docs/` — additional setup notes (e.g. Postgres)
- `prd.md` — product vision + user flow

---

## Quickstart (Local Dev)

### 1) Backend (FastAPI)
The backend runs on `http://localhost:8000` by default.

Prereqs: Python 3.12+ recommended

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`

### 2) Frontend (Next.js)
The frontend runs on `http://localhost:3000`.

Prereqs: Node.js 18+ recommended

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api/*` to the backend in development (see `frontend/next.config.ts`).

---

## Environment Variables

### Backend
Create a `.env` file in the repo root or inside `backend/`.

**Database**
- `DATABASE_URL` — defaults to SQLite (`sqlite+aiosqlite:///./iam_detective.db`)
- `DB_SSL` — `auto` | `require` | `disable`

**CORS**
- `CORS_ORIGINS` — comma-separated list. Defaults to `http://localhost:3000`

**AI Agent (required for the full experience)**
- `DO_AGENT_ENDPOINT`
- `DO_AGENT_ACCESS_KEY`

Optional per-case overrides:
- `DO_AGENT_ZODIAC_ENDPOINT` / `DO_AGENT_ZODIAC_ACCESS_KEY`
- `DO_AGENT_OJ_ENDPOINT` / `DO_AGENT_OJ_ACCESS_KEY`
- `DO_AGENT_AARUSHI_ENDPOINT` / `DO_AGENT_AARUSHI_ACCESS_KEY`
- `DO_AGENT_GSK_ENDPOINT` / `DO_AGENT_GSK_ACCESS_KEY`

### Frontend (optional)
- `NEXT_PUBLIC_BACKEND_URL` (e.g. `http://localhost:8000`)
- `APP_URL` (DigitalOcean App Platform injects this automatically)

---

## API Notes
- Most session endpoints require an `x-user-id` header (auto-generated and stored in localStorage by the frontend)
- Core API base: `/api` — e.g. `/api/cases`, `/api/me/cases`, `/api/sessions/{id}`

## Smoke Test (Backend)
```bash
cd backend
python smoke_test.py
```

---

## Where to Look Next
- Product flow and UX goals: `prd.md`
- Backend routes: `backend/app/main.py`
- Investigation engine + scoring: `backend/app/engine/`
- Frontend workspace UI: `frontend/app/case/[id]/workspace/page.tsx`
