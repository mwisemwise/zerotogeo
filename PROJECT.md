# Zero to GEO — Project Definition

## What We're Building

An AI Visibility & Citation Audit Platform that answers one question:

> "If a potential customer asks an AI system who they should use for this service in this area, does this business have a chance of being mentioned, recommended, or cited—and why?"

## What It Does

1. User enters a business URL
2. System crawls the website
3. System extracts structured signals (entity clarity, local/NAP, schema, content quality, authority, AI readiness)
4. System scores the business across six GEO pillars (0–100 each)
5. System generates evidence-backed findings and prioritized recommendations
6. User receives a full audit report with actionable fixes

## MVP Boundaries

**In scope:**
- Single business audit (one URL at a time)
- Six-pillar deterministic scoring engine
- Evidence-based findings (no hallucinated claims)
- Web-based report with pillar breakdowns
- FastAPI backend + React frontend
- SQLite database (PostgreSQL-ready schema)

**Out of scope (documented in docs/FUTURE.md):**
- User accounts / authentication
- Competitor analysis
- LLM-powered scoring (deterministic only for MVP)
- Scheduled re-audits
- Email delivery
- White-label reports
- Billing / subscriptions
- Mobile app

## Business Rules

1. **Evidence Rule:** Every finding must be traceable to something the system actually observed. No invented claims. If something cannot be verified, it is labeled "Not verified."
2. **Scoring Weights:** Business Entity Clarity (15%), Local/NAP Signals (15%), Structured Data (15%), Content/Answerability (20%), Authority/Trust (15%), AI Citation Readiness (20%).
3. **Score Classification:** 0–39 Poor, 40–59 Needs Work, 60–74 Good Foundation, 75–89 Strong, 90–100 Excellent.
4. **No LLM dependency for core scoring** — deterministic and reproducible.
5. **Robots.txt compliance** — always respected during crawling.

## Success Criteria

- A user can enter a URL and receive a complete GEO audit report within 60 seconds
- Every finding in the report has supporting evidence
- Scores are reproducible (same URL → same score, absent site changes)
- System handles malformed HTML, timeouts, and unreachable pages gracefully
