# Zero to GEO

**AI Visibility & Citation Audit Platform**

Zero to GEO analyzes a business website and produces a structured GEO (Generative Engine Optimization) audit. It answers the central question:

> "If a potential customer asks an AI system who they should use for this service in this area, does this business have a chance of being mentioned, recommended, or cited—and why?"

---

## What It Does

The platform crawls a business website, extracts structured signals, and scores the business across six GEO pillars:

| Pillar | Weight |
|---|---|
| Business Entity Clarity | 15% |
| Local / NAP Signals | 15% |
| Structured Data | 15% |
| Content / Answerability | 20% |
| Authority / Trust | 15% |
| AI Citation Readiness | 20% |

Each pillar produces a 0–100 score. The overall GEO Score is a weighted average.

Every finding is backed by evidence the system actually observed. No invented claims.

---

## GEO Score Classification

| Score | Classification |
|---|---|
| 0–39 | Poor |
| 40–59 | Needs Work |
| 60–74 | Good Foundation |
| 75–89 | Strong |
| 90–100 | Excellent |

---

## MVP Workflow

```
Landing Page → Enter Business → Create Audit → Website Crawl
→ Extract Business Information → Analyze GEO Signals
→ Calculate Score → Generate Findings → Prioritize Fixes → Audit Report
```

---

## Tech Stack

- **Backend:** Python 3.11+ / FastAPI
- **Frontend:** React 18 + Vite
- **Database:** SQLite (PostgreSQL-ready schema)
- **Crawling:** httpx + BeautifulSoup4
- **Analysis:** Deterministic (no LLM dependency for core scoring)

---

## Project Structure

```
zero-to-geo/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Settings and scoring weights
│   │   ├── api/               # Route handlers
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   └── services/
│   │       ├── crawler.py         # Website fetching + robots.txt
│   │       ├── extractor.py       # HTML parsing + data extraction
│   │       ├── geo_analyzer.py    # Six-pillar GEO analysis
│   │       ├── scoring.py         # Weighted score calculation
│   │       └── recommendations.py # Actionable recommendation engine
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── pages/             # Landing, AuditInput, Processing, Report
│   │   ├── components/        # Reusable UI components
│   │   ├── services/          # API client
│   │   └── App.jsx
│   └── package.json
│
├── docs/
│   ├── DECISIONS.md           # Architecture and design decisions
│   └── FUTURE.md              # Out-of-scope ideas for later
│
├── tests/                     # End-to-end tests
├── .env.example
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- pip

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/api/health`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## API Reference

```
POST /api/audits              Create a new audit
GET  /api/audits/{id}         Get audit status
GET  /api/audits/{id}/report  Get full audit report
GET  /api/health              Health check
```

---

## Evidence Rule

Every finding is traceable to something the system actually observed. The system will never claim:
- a business is cited by ChatGPT
- a schema exists unless detected
- a review exists unless found on the page
- a ranking unless measured

If something cannot be verified, it is labeled **Not verified**.

---

## Build Phases

- [x] Phase 1 — Repository and project skeleton
- [x] Phase 2 — FastAPI backend
- [x] Phase 3 — Database models
- [x] Phase 4 — Website crawler
- [x] Phase 5 — Content/entity/schema extraction
- [x] Phase 6 — Six-pillar GEO analyzer
- [x] Phase 7 — Scoring engine
- [x] Phase 8 — Findings/recommendation engine
- [x] Phase 9 — React frontend
- [x] Phase 10 — Audit report
- [x] Phase 11 — End-to-end testing
- [ ] Phase 12 — Polish

---

## Contributing

See `docs/DECISIONS.md` for architecture decisions.
See `docs/FUTURE.md` for planned features not yet in scope.

---

## License

Proprietary. All rights reserved.
