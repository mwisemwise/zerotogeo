"""
Zero to GEO — Customer-Facing Audit Report Schemas.

These schemas define the API response shapes for the customer audit report:
  - Page 1: YOUR CURRENT POSITION (ranking data)
  - Page 2: WHY YOU ARE WHERE YOU ARE (Five C's findings)
  - WHAT WE CAN FIX (organized solutions)
  - Validation workflow (status updates)

Rules:
  - No invented confidence scores or percentages
  - No technical jargon without explanation
  - Category must be: crawlability | clarity | content | credibility
  - Confidence is a summary, NOT a category
  - Competition is comparison data, NOT a category
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CUSTOMER_CATEGORIES = {"crawlability", "clarity", "content", "credibility"}
VALID_FINDING_STATUSES = {"open", "fixed", "verified"}

CATEGORY_EXPLANATIONS = {
    "crawlability": (
        "Your site needs to be easily accessible to Google and AI systems "
        "so they can find and process the information about your business."
    ),
    "clarity": (
        "Your website needs to make it easy for Google, AI, and customers "
        "to understand who you are, what you do, where you work, and what "
        "each page is about."
    ),
    "content": (
        "Your website needs to provide the useful, specific information "
        "customers, Google, and AI need to understand your services and "
        "answer questions about your business."
    ),
    "credibility": (
        "Your website needs to provide clear, consistent evidence that "
        "your business is legitimate, qualified, experienced, and trustworthy."
    ),
    "confidence": (
        "Your Google and AI confidence is the result of how well your "
        "website can be accessed, understood, supported by useful content, "
        "and backed by credible evidence."
    ),
}


# ---------------------------------------------------------------------------
# Customer Finding Schemas
# ---------------------------------------------------------------------------

class CustomerFindingResponse(BaseModel):
    """One finding in the customer-facing report."""
    id: str
    business_id: str
    audit_id: str
    category: str
    customer_finding: str
    evidence: str
    source_url: Optional[str] = None
    affected_page: Optional[str] = None
    severity: str
    recommended_fix: Optional[str] = None
    status: str
    verified: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CustomerFindingCreate(BaseModel):
    """Input for creating a customer finding."""
    business_id: str
    audit_id: str
    category: str
    technical_finding: str
    customer_finding: str
    evidence: str
    source_url: Optional[str] = None
    affected_page: Optional[str] = None
    severity: str = "medium"
    competitor_evidence: Optional[str] = None
    recommended_fix: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_CUSTOMER_CATEGORIES:
            raise ValueError(
                f"Category must be one of: {', '.join(sorted(VALID_CUSTOMER_CATEGORIES))}"
            )
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"critical", "high", "medium", "low"}:
            raise ValueError("Severity must be: critical, high, medium, or low")
        return v

    @field_validator("evidence")
    @classmethod
    def evidence_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Evidence must not be empty — findings require observed evidence.")
        return v


class FindingStatusUpdate(BaseModel):
    """Update the validation status of a finding."""
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_FINDING_STATUSES:
            raise ValueError(
                f"Status must be one of: {', '.join(sorted(VALID_FINDING_STATUSES))}"
            )
        return v


# ---------------------------------------------------------------------------
# Competitor / Ranking Schemas
# ---------------------------------------------------------------------------

class CompetitorRankingResponse(BaseModel):
    """One competitor's position in the ranking."""
    id: str
    competitor_name: str
    competitor_website: Optional[str] = None
    position: int
    is_subject: bool
    total_competitors: int
    ranking_type: str

    model_config = {"from_attributes": True}


class CompetitorEvidenceResponse(BaseModel):
    """Evidence of what a specific competitor is doing better."""
    id: str
    competitor_name: str
    evidence_summary: str
    category: Optional[str] = None
    source_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Category Summary (for the Five C's expandable sections)
# ---------------------------------------------------------------------------

class CategorySummary(BaseModel):
    """Summary of findings in one of the Four C categories."""
    category: str
    display_name: str
    explanation: str
    issue_count: int
    findings: List[CustomerFindingResponse]


class ConfidenceSummary(BaseModel):
    """
    Confidence is the resulting condition from the four categories.
    NOT a score. NOT a percentage. A diagnostic summary.
    """
    explanation: str
    summary: str
    contributing_issues: List[str]


# ---------------------------------------------------------------------------
# Fix Section Schema
# ---------------------------------------------------------------------------

class FixCategory(BaseModel):
    """Fixes organized under one of the Four C categories."""
    category: str
    display_name: str
    fixes: List[str]


# ---------------------------------------------------------------------------
# Full Customer Report Response
# ---------------------------------------------------------------------------

class CustomerReportResponse(BaseModel):
    """
    Full customer-facing audit report.

    Structure:
      Page 1 — YOUR CURRENT POSITION (rank, competitors)
      Page 2 — WHY YOU ARE WHERE YOU ARE (Five C's findings)
      WHAT WE CAN FIX (organized solutions)

    Rules:
      - No invented scores or confidence percentages
      - Rankings come from actual measured data
      - Findings require observed evidence
      - Never assume credentials are missing just because they're not on the site
    """

    # Business info
    business_id: str
    business_name: str
    business_city: str
    business_state: str
    business_category: str
    audit_id: str
    audit_created_at: str

    # Page 1 — YOUR CURRENT POSITION
    position: Optional[int] = None
    total_competitors: Optional[int] = None
    rankings: List[CompetitorRankingResponse] = []

    # Page 2 — WHY YOU ARE WHERE YOU ARE (Five C's)
    categories: List[CategorySummary] = []
    confidence: Optional[ConfidenceSummary] = None

    # Competitive comparison
    competitor_evidence: List[CompetitorEvidenceResponse] = []

    # WHAT WE CAN FIX
    fixes: List[FixCategory] = []

    model_config = {"from_attributes": True}
