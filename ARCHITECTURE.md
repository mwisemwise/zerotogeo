# Zero to GEO — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                        │
│              (Vite dev server / static build)             │
│         Landing → Audit Input → Processing → Report      │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP/JSON
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Backend                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│  │ API Layer│  │ Services │  │      Database          │ │
│  │          │  │          │  │                        │ │
│  │ /health  │──│ Crawler  │──│  SQLite (dev)          │ │
│  │ /audits  │  │ Extractor│  │  PostgreSQL (prod)     │ │
│  │          │  │ Analyzer │  │                        │ │
│  │          │  │ Scorer   │  │  Tables:               │ │
│  │          │  │ Recomm.  │  │  - audits              │ │
│  └──────────┘  └──────────┘  │  - pages              │ │
│                               │  - findings           │ │
│                               │  - recommendations    │ │
│                               └───────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend Framework | FastAPI (Python 3.11+) | Async-native, auto OpenAPI docs, Pydantic validation |
| Frontend | React 18 + Vite | Fast HMR, modern tooling, static build output |
| Database | SQLite → PostgreSQL | Zero-config dev, production-ready migration path |
| ORM | SQLAlchemy 2.0 | Database-agnostic, migration support via Alembic |
| Migrations | Alembic | Schema versioning, rollback support |
| HTTP Client | httpx | Async, timeout control, redirect handling |
| HTML Parser | BeautifulSoup4 + lxml | Handles malformed HTML gracefully |
| Validation | Pydantic | Request/response schema enforcement |

## Directory Layout

```
zero-to-geo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings, scoring weights
│   │   ├── database.py          # DB connection, session management
│   │   ├── api/                 # Route handlers
│   │   │   ├── health.py
│   │   │   └── audits.py
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── services/            # Business logic
│   │       ├── crawler.py       # Website fetching + robots.txt
│   │       ├── extractor.py     # HTML → structured data
│   │       ├── geo_analyzer.py  # Six-pillar analysis
│   │       ├── scoring.py       # Weighted score calculation
│   │       └── recommendations.py
│   ├── tests/
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── pages/               # Route-level components
│   │   ├── components/          # Reusable UI
│   │   └── services/            # API client
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│   ├── DECISIONS.md             # Architecture Decision Records
│   └── FUTURE.md               # Out-of-scope feature backlog
│
├── tests/                       # End-to-end / integration tests
├── scripts/                     # Dev automation
├── PROJECT.md                   # What we're building
├── ARCHITECTURE.md              # This file
├── TODO.md                      # Current work items
├── CHANGELOG.md                 # Release history
├── README.md                    # Setup and run instructions
├── .env.example                 # Environment template
└── .gitignore
```

## Data Flow: Audit Lifecycle

```
1. POST /api/audits {url: "https://example.com"}
   → Create audit record (status: pending)
   → Return audit ID

2. Background processing:
   a. Crawler fetches pages (respects robots.txt, follows links up to CRAWL_MAX_PAGES)
   b. Extractor parses HTML → structured signals
   c. GEO Analyzer scores each of 6 pillars
   d. Scorer computes weighted overall score
   e. Recommendation engine prioritizes fixes
   f. Update audit record (status: complete)

3. GET /api/audits/{id}/report
   → Return full audit with scores, findings, recommendations
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/health | Health check |
| POST | /api/audits | Create new audit |
| GET | /api/audits/{id} | Get audit status |
| GET | /api/audits/{id}/report | Get full report |

## Key Design Decisions

- **Deterministic scoring** — no LLM in the critical path (see docs/DECISIONS.md ADR-002)
- **Evidence-backed findings** — every finding has an `evidence` field
- **Database-agnostic** — SQLAlchemy abstraction allows SQLite↔PostgreSQL swap via connection string
- **API-first** — frontend and backend are independently deployable
- **Configuration-driven weights** — scoring tunable without code changes

## Deployment (Future)

- Backend: Docker container or cloud function
- Frontend: Static build (Vite → dist/) served from CDN or S3
- Database: Managed PostgreSQL (RDS, Supabase, etc.)
