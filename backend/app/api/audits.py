"""
Zero to GEO — Audit API endpoints.

Routes:
  POST /api/audits              Create a new audit and start processing
  GET  /api/audits/{id}         Get audit status (for frontend polling)
  GET  /api/audits/{id}/report  Get full GEO report (only when complete)

Audit pipeline runs in a background thread so the POST returns immediately
with the audit ID. The frontend polls GET /api/audits/{id} until
status = complete | failed.

Pipeline (phases 4–8 will fill in the real implementations):
  1. Crawl website
  2. Extract business information
  3. Analyze six GEO pillars
  4. Calculate weighted score
  5. Generate findings and recommendations
  6. Persist results, mark complete
"""

import threading
import traceback
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Business, Audit, PillarResult, Finding
from app.schemas.schemas import (
    AuditCreate,
    AuditStatusResponse,
    AuditReportResponse,
    BusinessResponse,
    PillarResultResponse,
    FindingResponse,
    ActionPlanItem,
    PILLAR_DISPLAY_NAMES,
)
from app.config import GeoScoreClassification, ScoringWeights
from app.services.pipeline import run_audit_pipeline

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /api/audits — create and start audit
# ---------------------------------------------------------------------------

@router.post("", response_model=AuditStatusResponse, status_code=202)
def create_audit(
    payload: AuditCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a new GEO audit for a business.

    Returns 202 Accepted immediately with the audit ID and status=pending.
    The audit runs asynchronously in the background.
    Poll GET /api/audits/{id} to track progress.
    """
    # Create business record
    business = Business(
        name=payload.business_name,
        website=payload.website_url,
        city=payload.city,
        state=payload.state,
        category=payload.category,
    )
    db.add(business)
    db.flush()  # Get the business.id without committing

    # Create audit record (starts as pending)
    audit = Audit(business_id=business.id)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    db.refresh(business)

    # Start the pipeline in the background
    background_tasks.add_task(run_audit_pipeline, audit_id=audit.id)

    return AuditStatusResponse(
        id=audit.id,
        status=audit.status,
        overall_score=audit.overall_score,
        error_message=audit.error_message,
        created_at=audit.created_at,
        completed_at=audit.completed_at,
        business=BusinessResponse.model_validate(business),
    )


# ---------------------------------------------------------------------------
# GET /api/audits/{id} — poll status
# ---------------------------------------------------------------------------

@router.get("/{audit_id}", response_model=AuditStatusResponse)
def get_audit(audit_id: str, db: Session = Depends(get_db)):
    """
    Get the current status of an audit.

    Used by the frontend polling loop.
    Returns status, score (when complete), and error_message (when failed).
    """
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    return AuditStatusResponse(
        id=audit.id,
        status=audit.status,
        overall_score=audit.overall_score,
        error_message=audit.error_message,
        created_at=audit.created_at,
        completed_at=audit.completed_at,
        business=BusinessResponse.model_validate(audit.business),
    )


# ---------------------------------------------------------------------------
# GET /api/audits/{id}/report — full GEO report
# ---------------------------------------------------------------------------

@router.get("/{audit_id}/report", response_model=AuditReportResponse)
def get_audit_report(audit_id: str, db: Session = Depends(get_db)):
    """
    Get the full GEO report for a completed audit.

    Returns 404 if audit not found.
    Returns 409 if audit is not yet complete.
    Returns 422 if audit failed (with error detail).
    """
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    if audit.status == "failed":
        raise HTTPException(
            status_code=422,
            detail=f"Audit failed: {audit.error_message or 'Unknown error.'}",
        )

    if audit.status != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"Audit is not complete yet (status: {audit.status}).",
        )

    # Build pillar result responses
    pillar_responses = [
        PillarResultResponse.from_orm_with_display(p)
        for p in sorted(audit.pillar_results, key=lambda p: p.pillar)
    ]

    # Build finding responses — problems first (by severity), then positives
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "positive": 4}
    sorted_findings = sorted(
        audit.findings,
        key=lambda f: (severity_order.get(f.severity, 99), f.priority or "P9"),
    )
    finding_responses = [
        FindingResponse.from_orm_with_display(f) for f in sorted_findings
    ]

    # Build action plan from findings (exclude positives, require recommendation)
    action_plan = _build_action_plan(audit.findings)

    # Executive summary
    summary = _build_summary(
        audit.overall_score,
        GeoScoreClassification.classify(audit.overall_score),
        audit.business,
        pillar_responses,
        finding_responses,
    )

    return AuditReportResponse(
        id=audit.id,
        status=audit.status,
        overall_score=audit.overall_score,
        classification=GeoScoreClassification.classify(audit.overall_score),
        summary=summary,
        created_at=audit.created_at,
        completed_at=audit.completed_at,
        business=BusinessResponse.model_validate(audit.business),
        pillar_results=pillar_responses,
        findings=finding_responses,
        action_plan=action_plan,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_action_plan(findings) -> list[ActionPlanItem]:
    """
    Build a prioritized action plan from findings.
    Only includes findings that have a recommendation and a priority.
    Excludes positive findings.
    """
    items = []
    seen = set()
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

    actionable = [
        f for f in findings
        if f.severity != "positive"
        and f.recommendation
        and f.priority
    ]
    actionable.sort(key=lambda f: priority_order.get(f.priority, 9))

    for finding in actionable:
        key = finding.recommendation[:80]
        if key not in seen:
            seen.add(key)
            items.append(ActionPlanItem(
                priority=finding.priority,
                description=finding.recommendation,
                pillar=finding.pillar,
                pillar_display=PILLAR_DISPLAY_NAMES.get(finding.pillar, finding.pillar),
            ))

    return items


def _build_summary(
    score: float,
    classification: str,
    business,
    pillars: list[PillarResultResponse],
    findings: list[FindingResponse],
) -> str:
    """
    Build a plain-English executive summary from the audit results.
    This is deterministic — no LLM required.
    """
    name = business.name
    location = f"{business.city}, {business.state}"
    category = business.category

    # Weakest and strongest pillars
    if pillars:
        weakest = min(pillars, key=lambda p: p.score)
        strongest = max(pillars, key=lambda p: p.score)
    else:
        weakest = strongest = None

    # Count critical/high findings
    critical_count = sum(1 for f in findings if f.severity == "critical")
    high_count = sum(1 for f in findings if f.severity == "high")
    positive_count = sum(1 for f in findings if f.severity == "positive")

    parts = [
        f"{name} ({category} in {location}) received a GEO Score of {round(score)}/100 — {classification}.",
    ]

    if weakest and weakest.score < 60:
        parts.append(
            f"The weakest area is {weakest.pillar_display} ({round(weakest.score)}/100), "
            f"which represents the highest opportunity for improvement."
        )

    if strongest and strongest.score >= 70:
        parts.append(
            f"The strongest area is {strongest.pillar_display} ({round(strongest.score)}/100)."
        )

    if critical_count > 0:
        parts.append(
            f"There {'is' if critical_count == 1 else 'are'} {critical_count} critical issue{'s' if critical_count != 1 else ''} "
            f"that should be addressed immediately."
        )
    elif high_count > 0:
        parts.append(
            f"There {'is' if high_count == 1 else 'are'} {high_count} high-priority issue{'s' if high_count != 1 else ''} identified."
        )

    if positive_count > 0:
        parts.append(
            f"The audit also identified {positive_count} existing strength{'s' if positive_count != 1 else ''} to build on."
        )

    return " ".join(parts)
