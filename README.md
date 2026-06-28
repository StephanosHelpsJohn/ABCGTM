# Fetch AI 🐕

> AI-powered sales automation — enrich leads, draft personalized outreach, generate branded microsites, and intercept competitor replies in seconds.

Fetch AI is a full-stack sales automation platform built with FastAPI + GPT-4o + Orange Slice. Drop in a company domain, and Fetch enriches the prospect with real firmographic and intent data, drafts a hyper-personalized cold email, and generates a tailored microsite — all in under 10 seconds.

---

## Modules

| Module | What it does |
|---|---|
| **Generate Leads** | Domain → Orange Slice enrichment → GPT-4o email draft → personalized HTML microsite |
| **CRM** | Manage enriched contacts and companies saved from previous runs |
| **Generate Decks** | Paste any company URL → Fetch reads the site, extracts brand voice + visual identity, generates an HTML microsite in that style |
| **Event Listeners** | Scan a domain for buy signals (Series A raise, key job postings) → AI drafts an email that references the *exact* triggering event |
| **Competitor Trap** | Paste a prospect reply that mentions a competitor → AI identifies the competitor and drafts a response with specific advantages + a dynamically generated comparison table |

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+ (for Orange Slice enrichment)
- **Orange Slice** — install with `npx orangeslice@latest` (auth key saved to `~/.config/orangeslice/config.json`)
- **OpenAI API key** — GPT-4o access required

---

## Installation

```bash
git clone https://github.com/StephanosHelpsJohn/ABCGTM
cd ABCGTM

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node dependencies (Orange Slice)
npm install
npx orangeslice@latest   # authenticates and writes config
```

---

## Environment

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite+aiosqlite:///./abcgtm.db
OPENAI_API_KEY=sk-proj-...
BASE_URL=http://localhost:8000
```

> **Note:** If your shell has `OPENAI_API_KEY` set to something else (e.g. a local Ollama key), Fetch AI reads the `.env` file directly so the right key always wins.

---

## Running

```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000).

---

## How it works

```
Domain + Persona
     │
     ▼
Orange Slice (Node.js subprocess)
  ├── LinkedIn company enrichment (firmographics, headcount, funding)
  ├── News events (financing rounds, key hires, expansions)
  └── Technology detections (tech stack)
     │
     ▼
GPT-4o Email Drafter
  └── Cold email referencing actual signals, under 150 words
     │
     ▼
GPT-4o Microsite Generator
  └── Full HTML landing page, personalized per prospect
     │
     ▼
Telemetry
  └── Pings back on page view + pricing click (logged to console)
```

---

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), SQLite (aiosqlite)
- **AI:** OpenAI GPT-4o
- **Enrichment:** Orange Slice (npm)
- **Frontend:** Tailwind CSS (CDN), vanilla JS, pixel art canvas animation
- **Database:** SQLite (dev) — swap `DATABASE_URL` for Postgres in production

---

## Project Structure

```
ABCGTM/
├── main.py                  # FastAPI app, lifespan, mounts
├── core/
│   ├── config.py            # Settings, .env reader
│   └── database.py          # Async engine + session factory
├── models/
│   └── database.py          # SQLAlchemy ORM models
├── routers/
│   ├── campaign.py          # POST /api/v1/campaign/generate
│   ├── execution.py         # POST /api/v1/campaign/send
│   ├── webhooks.py          # POST /api/v1/webhooks/telemetry
│   ├── crm.py               # GET/POST /api/v1/crm/contacts
│   ├── decks.py             # POST /api/v1/decks/generate
│   ├── events.py            # POST /api/v1/events/scan
│   └── competitor.py        # POST /api/v1/competitor/analyze
├── services/
│   ├── agent_service.py     # Core pipeline (enrich → draft → microsite)
│   ├── deck_service.py      # Brand extraction + microsite generation
│   ├── event_service.py     # Buy signal scanning + event-triggered emails
│   └── competitor_service.py # Competitor analysis + comparison table
├── scripts/
│   └── enrich.mjs           # Orange Slice Node.js enrichment script
└── static/
    ├── index.html           # Dashboard UI
    └── microsites/          # Generated HTML microsites (auto-created)
```

---

## Deploying

For production, swap SQLite for PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
```

and install `asyncpg` instead of `aiosqlite`.

---

Built by [Gamerplug](https://gamerplug.gg) · Confidential & Proprietary
