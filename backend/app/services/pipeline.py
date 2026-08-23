"""
Zero to GEO — Audit pipeline orchestrator.

This module sequences all audit phases and updates the audit status as each
phase completes. It runs in a FastAPI BackgroundTask (separate thread).

Current state (Phase 2):
  The pipeline runs the full status lifecycle and produces a real
  (though basic) analysis. Phases 4-8 will replace each stub step
  with real implementations.

Pipeline:
  pending → crawling → extracting → analyzing → scoring → complete
                                                         ↘ failed (on any error)

EVIDENCE RULE: Every finding must have evidence. Stubs are clearly labeled
as stubs so they are never shipped as real results.
"""

import traceback
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import Audit, PillarResult, Finding
from app.config import ScoringWeights, GeoScoreClassification


def run_audit_pipeline(audit_id: str) -> None:
    """
    Run the full GEO audit pipeline for the given audit ID.

    Creates its own database session (runs in a background thread,
    separate from the request session).
    """
    db = SessionLocal()
    try:
        _run(audit_id, db)
    except Exception as exc:
        # Last-resort error handler — ensure the audit is never left in
        # a non-terminal state.
        try:
            audit = db.get(Audit, audit_id)
            if audit and audit.status not in ("complete", "failed"):
                audit.mark_failed(f"Unexpected pipeline error: {str(exc)[:500]}")
                db.commit()
        except Exception:
            pass  # Nothing more we can do
    finally:
        db.close()


def _run(audit_id: str, db: Session) -> None:
    """Inner pipeline — raises on error, caller handles marking failed."""

    audit = db.get(Audit, audit_id)
    if not audit:
        return  # Audit was deleted before pipeline started

    business = audit.business

    # ---- PHASE 4 (stub): Crawl ----
    _set_status(db, audit, "crawling")

    from app.services.crawler import crawl_website
    crawl_result = crawl_website(
        url=business.website,
        user_agent=_get_user_agent(),
        timeout=_get_timeout(),
        respect_robots=_get_respect_robots(),
    )

    if not crawl_result.success:
        audit.mark_failed(crawl_result.error or "Website could not be crawled.")
        db.commit()
        return

    # ---- PHASE 5 (stub): Extract ----
    _set_status(db, audit, "extracting")

    from app.services.extractor import extract_content
    extracted = extract_content(crawl_result.html, crawl_result.url)

    # ---- PHASE 6 (stub): Analyze ----
    _set_status(db, audit, "analyzing")

    from app.services.geo_analyzer import analyze
    pillar_scores = analyze(extracted, business)

    # ---- PHASE 7: Score ----
    _set_status(db, audit, "scoring")

    from app.services.scoring import calculate_overall_score
    overall_score = calculate_overall_score(pillar_scores)

    # ---- PHASE 8 (stub): Findings + Recommendations ----
    from app.services.recommendations import generate_findings
    findings_data = generate_findings(pillar_scores, extracted, business)

    # ---- Persist results ----
    _persist_results(db, audit, pillar_scores, findings_data, overall_score)


def _set_status(db: Session, audit: Audit, status: str) -> None:
    """Update audit status and commit so the frontend can see progress."""
    audit.status = status
    db.commit()


def _persist_results(db, audit, pillar_scores, findings_data, overall_score):
    """Write pillar results and findings, then mark the audit complete."""

    pillar_display = {
        "entity_clarity": "Business Entity Clarity",
        "local_signals": "Local / NAP Signals",
        "structured_data": "Structured Data",
        "content": "Content / Answerability",
        "authority": "Authority / Trust",
        "citation_readiness": "AI Citation Readiness",
    }

    for pillar_key, pillar_data in pillar_scores.items():
        pr = PillarResult(
            audit_id=audit.id,
            pillar=pillar_key,
            score=pillar_data["score"],
            summary=pillar_data.get("summary", ""),
        )
        db.add(pr)

    for finding_data in findings_data:
        f = Finding(
            audit_id=audit.id,
            pillar=finding_data["pillar"],
            severity=finding_data["severity"],
            title=finding_data["title"],
            finding=finding_data["finding"],
            evidence=finding_data.get("evidence", ""),
            recommendation=finding_data.get("recommendation", ""),
            priority=finding_data.get("priority", "P2"),
        )
        db.add(f)

    audit.mark_complete(overall_score)
    db.commit()


def _get_user_agent() -> str:
    from app.config import settings
    return settings.crawl_user_agent


def _get_timeout() -> int:
    from app.config import settings
    return settings.crawl_timeout_seconds


def _get_respect_robots() -> bool:
    from app.config import settings
    return settings.crawl_respect_robots
