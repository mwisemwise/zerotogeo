"""
Zero to GEO — Customer-Facing Audit Report API.

Endpoints:
  GET  /api/customer-report/{audit_id}         Full customer report
  GET  /api/customer-report/{audit_id}/findings Customer findings for an audit
  PATCH /api/customer-report/findings/{id}/status  Update finding status
  POST /api/customer-report/{audit_id}/findings    Create a customer finding
  POST /api/customer-report/{audit_id}/rankings    Add competitor ranking data
  POST /api/customer-report/{audit_id}/evidence    Add competitor evidence

This is the customer-facing translation layer on top of the technical audit.
The technical audit engine remains unchanged.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Audit, Business
from app.models.customer_audit import (
    CustomerFinding,
    CompetitorRanking,
    CompetitorEvidence,
    VALID_CUSTOMER_CATEGORIES,
)
from app.schemas.customer_audit import (
    CustomerReportResponse,
    CustomerFindingResponse,
    CustomerFindingCreate,
    FindingStatusUpdate,
    CompetitorRankingResponse,
    CompetitorEvidenceResponse,
    CategorySummary,
    ConfidenceSummary,
    FixCategory,
    CATEGORY_EXPLANATIONS,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/customer-report/{audit_id} — Full customer report
# ---------------------------------------------------------------------------

@router.get("/{audit_id}", response_model=CustomerReportResponse)
def get_customer_report(audit_id: str, db: Session = Depends(get_db)):
    """
    Get the full customer-facing audit report.

    Returns:
      - Page 1: Current position and competitor rankings
      - Page 2: Five C's findings with evidence
      - Competitive comparison evidence
      - What can be fixed (organized by category)
    """
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    if audit.status != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"Audit is not complete yet (status: {audit.status}).",
        )

    business = audit.business

    # Fetch customer findings
    findings = (
        db.query(CustomerFinding)
        .filter(CustomerFinding.audit_id == audit_id)
        .order_by(CustomerFinding.category, CustomerFinding.severity)
        .all()
    )

    # Fetch rankings
    rankings = (
        db.query(CompetitorRanking)
        .filter(CompetitorRanking.audit_id == audit_id)
        .order_by(CompetitorRanking.ranking_type, CompetitorRanking.position)
        .all()
    )

    # Fetch competitor evidence
    comp_evidence = (
        db.query(CompetitorEvidence)
        .filter(CompetitorEvidence.audit_id == audit_id)
        .order_by(CompetitorEvidence.competitor_name)
        .all()
    )

    # Determine position
    subject_ranking = next(
        (r for r in rankings if r.is_subject), None
    )
    position = subject_ranking.position if subject_ranking else None
    total_competitors = subject_ranking.total_competitors if subject_ranking else None

    # Build category summaries (the Four C's)
    categories = _build_category_summaries(findings)

    # Build confidence summary (derived from the four categories)
    confidence = _build_confidence_summary(findings, categories)

    # Build fix section
    fixes = _build_fixes(findings)

    return CustomerReportResponse(
        business_id=business.id,
        business_name=business.name,
        business_city=business.city,
        business_state=business.state,
        business_category=business.category,
        audit_id=audit.id,
        audit_created_at=audit.created_at,
        position=position,
        total_competitors=total_competitors,
        rankings=[
            CompetitorRankingResponse.model_validate(r) for r in rankings
        ],
        categories=categories,
        confidence=confidence,
        competitor_evidence=[
            CompetitorEvidenceResponse.model_validate(e) for e in comp_evidence
        ],
        fixes=fixes,
    )


# ---------------------------------------------------------------------------
# GET /api/customer-report/{audit_id}/findings — All findings
# ---------------------------------------------------------------------------

@router.get("/{audit_id}/findings", response_model=List[CustomerFindingResponse])
def get_customer_findings(audit_id: str, db: Session = Depends(get_db)):
    """Get all customer findings for an audit."""
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    findings = (
        db.query(CustomerFinding)
        .filter(CustomerFinding.audit_id == audit_id)
        .order_by(CustomerFinding.category, CustomerFinding.severity)
        .all()
    )

    return [CustomerFindingResponse.model_validate(f) for f in findings]


# ---------------------------------------------------------------------------
# PATCH /api/customer-report/findings/{id}/status — Update status
# ---------------------------------------------------------------------------

@router.patch("/findings/{finding_id}/status", response_model=CustomerFindingResponse)
def update_finding_status(
    finding_id: str,
    payload: FindingStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update the validation status of a customer finding.

    Status transitions:
      open → fixed    (business claims it's fixed)
      fixed → verified (re-audit confirms the fix)
      fixed → open    (re-audit found it's still a problem)
      verified → open (regression detected)
    """
    finding = db.get(CustomerFinding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    new_status = payload.status

    if new_status == "fixed":
        finding.mark_fixed()
    elif new_status == "verified":
        finding.mark_verified()
    elif new_status == "open":
        finding.reopen()

    db.commit()
    db.refresh(finding)

    return CustomerFindingResponse.model_validate(finding)


# ---------------------------------------------------------------------------
# POST /api/customer-report/{audit_id}/findings — Create finding
# ---------------------------------------------------------------------------

@router.post("/{audit_id}/findings", response_model=CustomerFindingResponse, status_code=201)
def create_customer_finding(
    audit_id: str,
    payload: CustomerFindingCreate,
    db: Session = Depends(get_db),
):
    """Create a new customer-facing finding for an audit."""
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    finding = CustomerFinding(
        business_id=payload.business_id,
        audit_id=audit_id,
        category=payload.category,
        technical_finding=payload.technical_finding,
        customer_finding=payload.customer_finding,
        evidence=payload.evidence,
        source_url=payload.source_url,
        affected_page=payload.affected_page,
        severity=payload.severity,
        competitor_evidence=payload.competitor_evidence,
        recommended_fix=payload.recommended_fix,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    return CustomerFindingResponse.model_validate(finding)


# ---------------------------------------------------------------------------
# POST /api/customer-report/{audit_id}/rankings — Add ranking data
# ---------------------------------------------------------------------------

@router.post("/{audit_id}/rankings", response_model=List[CompetitorRankingResponse], status_code=201)
def add_competitor_rankings(
    audit_id: str,
    rankings: List[dict],
    db: Session = Depends(get_db),
):
    """Add competitor ranking data for an audit."""
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    created = []
    for rank_data in rankings:
        ranking = CompetitorRanking(
            audit_id=audit_id,
            business_id=audit.business_id,
            ranking_type=rank_data.get("ranking_type", "google"),
            market=rank_data.get("market"),
            service_area=rank_data.get("service_area"),
            competitor_name=rank_data["competitor_name"],
            competitor_website=rank_data.get("competitor_website"),
            position=rank_data["position"],
            is_subject=rank_data.get("is_subject", False),
            total_competitors=rank_data["total_competitors"],
        )
        db.add(ranking)
        created.append(ranking)

    db.commit()
    for r in created:
        db.refresh(r)

    return [CompetitorRankingResponse.model_validate(r) for r in created]


# ---------------------------------------------------------------------------
# POST /api/customer-report/{audit_id}/evidence — Add competitor evidence
# ---------------------------------------------------------------------------

@router.post("/{audit_id}/evidence", response_model=List[CompetitorEvidenceResponse], status_code=201)
def add_competitor_evidence(
    audit_id: str,
    evidence_list: List[dict],
    db: Session = Depends(get_db),
):
    """Add competitor evidence for an audit."""
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    created = []
    for ev_data in evidence_list:
        evidence = CompetitorEvidence(
            audit_id=audit_id,
            business_id=audit.business_id,
            competitor_name=ev_data["competitor_name"],
            evidence_summary=ev_data["evidence_summary"],
            category=ev_data.get("category"),
            source_url=ev_data.get("source_url"),
        )
        db.add(evidence)
        created.append(evidence)

    db.commit()
    for e in created:
        db.refresh(e)

    return [CompetitorEvidenceResponse.model_validate(e) for e in created]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

CATEGORY_DISPLAY_NAMES = {
    "crawlability": "CRAWLABILITY",
    "clarity": "CLARITY",
    "content": "CONTENT",
    "credibility": "CREDIBILITY",
}


def _build_category_summaries(findings: list) -> List[CategorySummary]:
    """Build the Four C category summaries from findings."""
    categories = []

    for cat in VALID_CUSTOMER_CATEGORIES:
        cat_findings = [f for f in findings if f.category == cat and f.status != "verified"]
        cat_findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))

        categories.append(CategorySummary(
            category=cat,
            display_name=CATEGORY_DISPLAY_NAMES[cat],
            explanation=CATEGORY_EXPLANATIONS[cat],
            issue_count=len(cat_findings),
            findings=[CustomerFindingResponse.model_validate(f) for f in cat_findings],
        ))

    return categories


def _build_confidence_summary(
    findings: list,
    categories: List[CategorySummary],
) -> ConfidenceSummary:
    """
    Build the Confidence summary.
    Confidence is the resulting condition — NOT a score.
    It summarizes what's hurting the business across all four categories.
    """
    # Collect the main issues contributing to low confidence
    contributing_issues = []
    open_findings = [f for f in findings if f.status != "verified"]

    # Group by severity for the summary
    critical_count = sum(1 for f in open_findings if f.severity == "critical")
    high_count = sum(1 for f in open_findings if f.severity == "high")

    # Build contributing issues from the most impactful findings
    for f in sorted(open_findings, key=lambda x: SEVERITY_ORDER.get(x.severity, 99)):
        if len(contributing_issues) >= 5:
            break
        contributing_issues.append(f.customer_finding)

    # Build natural language summary
    category_issues = []
    for cat in categories:
        if cat.issue_count > 0:
            category_issues.append(cat.display_name.lower())

    if category_issues:
        issue_str = ", ".join(category_issues[:-1])
        if len(category_issues) > 1:
            issue_str += f", and {category_issues[-1]}"
        else:
            issue_str = category_issues[0]
        summary = (
            f"Your current position is being affected by problems with {issue_str}."
        )
    else:
        summary = (
            "No significant issues were identified affecting your position."
        )

    return ConfidenceSummary(
        explanation=CATEGORY_EXPLANATIONS["confidence"],
        summary=summary,
        contributing_issues=contributing_issues,
    )


def _build_fixes(findings: list) -> List[FixCategory]:
    """
    Build the WHAT WE CAN FIX section.
    Organizes fixes under the Four C categories.
    Only includes findings with a recommended fix that are still open.
    """
    fixes = []

    for cat in VALID_CUSTOMER_CATEGORIES:
        cat_findings = [
            f for f in findings
            if f.category == cat
            and f.recommended_fix
            and f.status != "verified"
        ]
        cat_findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))

        fix_list = []
        seen = set()
        for f in cat_findings:
            fix_text = f.recommended_fix.strip()
            if fix_text and fix_text not in seen:
                seen.add(fix_text)
                fix_list.append(fix_text)

        if fix_list:
            fixes.append(FixCategory(
                category=cat,
                display_name=CATEGORY_DISPLAY_NAMES[cat],
                fixes=fix_list,
            ))

    return fixes
