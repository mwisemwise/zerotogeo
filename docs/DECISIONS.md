# Zero to GEO — Architecture Decision Record

This file records significant technical decisions. Each decision includes context, the choice made, and the rationale.

Routine implementation details are not recorded here. This file tracks decisions that affect architecture, product direction, scope, or future maintainability.

---

## Decision Format

```
## ADR-NNN — Title
Date: YYYY-MM-DD
Status: Accepted | Superseded | Deprecated

### Context
What situation required a decision.

### Decision
What was chosen.

### Rationale
Why this choice was made.

### Consequences
What this decision enables or constrains.
```

---

## ADR-001 — SQLite for MVP Database

Date: 2026-08-11
Status: Accepted

### Context

The MVP needs a database. Options include SQLite, PostgreSQL, MySQL. The system needs to be easy to run locally without external services during development.

### Decision

Use SQLite for the MVP via SQLAlchemy ORM.

### Rationale

- Zero configuration for local development
- Single file database, easy to inspect and reset
- SQLAlchemy abstraction means PostgreSQL can be substituted later by changing the connection string and driver
- Appropriate for MVP scale (single-user, sequential audits)

### Consequences

- Cannot support concurrent high-load production traffic without migrating to PostgreSQL
- Migration path is straightforward: change `DATABASE_URL` in `.env`, install `asyncpg` or `psycopg2`, run migrations
- No stored procedures or database-specific features used, keeping migration clean

---

## ADR-002 — Deterministic Analysis, No LLM Dependency for Core Scoring

Date: 2026-08-11
Status: Accepted

### Context

The MVP must be useful without an external AI API. LLM APIs add cost, latency, rate limits, and failure modes.

### Decision

The core scoring engine is fully deterministic. All six GEO pillars are scored using rule-based analysis of crawled content.

### Rationale

- Eliminates LLM API cost for every audit run
- Makes scoring reproducible and explainable
- Avoids external dependency failures
- Deterministic rules can be audited and adjusted
- LLM enhancement can be added as an optional overlay in a future phase

### Consequences

- Scoring quality is limited by rule sophistication
- Some nuanced content quality signals will be approximate
- Future: LLM can be added as an enhancement layer to improve finding explanations and semantic analysis without replacing the core engine

---

## ADR-003 — Scoring Weights Stored in Configuration

Date: 2026-08-11
Status: Accepted

### Context

Pillar weights (e.g., Content = 20%, Entity Clarity = 15%) will likely need tuning as the product matures. Hard-coding weights in analysis logic would require code changes for every adjustment.

### Decision

All pillar weights are stored in `backend/app/config.py` as a named configuration object, not scattered throughout analysis code.

### Rationale

- Single place to adjust weights
- Weights can be exposed as admin settings in a future phase
- Different weight profiles could serve different business types (local service vs. e-commerce vs. SaaS)

### Consequences

- Any weight change requires only a config update, not code surgery
- Weight config should be validated to ensure weights sum to 1.0

---

## ADR-004 — httpx + BeautifulSoup4 for Crawling and Parsing

Date: 2026-08-11
Status: Accepted

### Context

The crawler needs to fetch web pages reliably. Options include requests, httpx, aiohttp, Selenium/Playwright (browser-based).

### Decision

Use `httpx` for HTTP requests and `BeautifulSoup4` for HTML parsing.

### Rationale

- `httpx` supports async, timeouts, redirect handling, and SSL control out of the box
- `BeautifulSoup4` is a proper parser — not regex — and handles malformed HTML gracefully
- Browser-based crawling (Playwright) is overkill for MVP and adds complexity
- `lxml` parser backend for BeautifulSoup4 provides speed and robustness

### Consequences

- JavaScript-rendered content will not be visible (acceptable for MVP; most business websites render critical content server-side)
- Future: Playwright integration for JS-heavy sites can be added as an optional crawl mode

---

## ADR-005 — React + Vite for Frontend

Date: 2026-08-11
Status: Accepted

### Context

Frontend needs to be a modern single-page app that communicates with the FastAPI backend.

### Decision

React 18 with Vite as the build tool.

### Rationale

- Vite provides fast development server with hot module replacement
- React is well-understood with broad ecosystem support
- No need for SSR/Next.js for MVP (no SEO requirements on the tool itself for MVP)
- Keeps frontend simple and deployable as static files

### Consequences

- Frontend is a separate dev server (port 5173) from backend (port 8000) during development
- CORS must be configured on the FastAPI backend
- Production deployment: build to static files, serve from CDN or alongside backend

---

## ADR-006 — Evidence Rule Enforcement

Date: 2026-08-11
Status: Accepted

### Context

The product's core promise is honest, evidence-based analysis. Every finding must be traceable to something the system actually observed.

### Decision

The Finding data model includes a required `evidence` field. The analysis services must populate this field with the actual observed data that led to the finding. Analysis code is prohibited from constructing findings without evidence.

### Rationale

- Prevents the system from manufacturing claims
- Builds user trust
- Distinguishes Zero to GEO from generic SEO tools that make unsupported claims
- Makes the system auditable

### Consequences

- Every finding takes more effort to construct correctly
- "Not verified" is a valid and required label when something cannot be checked
- Quality of evidence descriptions is a product quality metric

---

## ADR-007 — API-First Architecture

Date: 2026-08-11
Status: Accepted

### Context

Backend and frontend are separate applications. The backend must expose a clean JSON API.

### Decision

FastAPI backend exposes a versioned JSON API. The frontend communicates exclusively via this API. No server-side rendering of HTML from the backend.

### Rationale

- Clean separation of concerns
- Frontend can be replaced or supplemented without changing the backend
- API can serve future mobile clients, integrations, or white-label products
- FastAPI auto-generates OpenAPI documentation

### Consequences

- CORS configuration required during development
- Both services must be running for full functionality
- API contracts must be stable once frontend depends on them

---
