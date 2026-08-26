"""
Zero to GEO — Customer-Facing Audit Models.

These models support the customer-facing audit report:
  - CustomerFinding: Structured findings mapped to the Five C's framework
  - CompetitorRanking: Position data for competitive comparison
  - CompetitorEvidence: What competitors are doing better

The Five C customer-facing categories:
  crawlability — site accessible to Google/AI
  clarity      — easy to understand who/what/where
  content      — useful, specific information
  credibility  — legitimate, qualified, trustworthy evidence

Confidence is NOT a category — it's the resulting condition
calculated from the four categories above.

Competition/ranking is separate data, not a category.

Design rules:
  - Never invent scores or confidence percentages
  - Never assume something is missing just because it's not on the site
  - Every finding must have evidence the system actually observed
  - Category must be one of: crawlability, clarity, content, credibility
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.models.models import Base


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_uuid() -> str:
    return str(uuid.uuid4())


# Valid categories for customer findings (NOT confidence — that's derived)
VALID_CUSTOMER_CATEGORIES = ("crawlability", "clarity", "content", "credibility")

# Valid statuses for the validation workflow
VALID_FINDING_STATUSES = ("open", "fixed", "verified")


# ---------------------------------------------------------------------------
# CustomerFinding
# ---------------------------------------------------------------------------

class CustomerFinding(Base):
    """
    A structured finding for the customer-facing audit report.

    Maps technical audit findings to the Five C's framework
    using customer-friendly language.

    Category MUST be one of: crawlability, clarity, content, credibility.
    Confidence is calculated/summarized from these findings — NOT stored here.

    Status workflow:
      open → fixed → verified (re-audit confirms fix)
    """
    __tablename__ = "customer_finding"

    id = Column(String, primary_key=True, default=_new_uuid)
    business_id = Column(
        String,
        ForeignKey("business.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audit_id = Column(
        String,
        ForeignKey("audit.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Five C's category: crawlability | clarity | content | credibility
    category = Column(String, nullable=False)

    # Technical finding (internal — not shown to customer)
    technical_finding = Column(Text, nullable=False)

    # Customer-facing finding (plain language, no jargon)
    customer_finding = Column(Text, nullable=False)

    # What the system actually observed (must not be blank)
    evidence = Column(Text, nullable=False)

    # The URL where the evidence was found
    source_url = Column(String, nullable=True)

    # The specific page affected
    affected_page = Column(String, nullable=True)

    # Severity: critical | high | medium | low
    severity = Column(String, nullable=False, default="medium")

    # What competitors are doing better (if applicable)
    competitor_evidence = Column(Text, nullable=True)

    # Business-level recommended fix (customer language)
    recommended_fix = Column(Text, nullable=True)

    # Validation workflow status: open | fixed | verified
    status = Column(String, nullable=False, default="open")

    # Has this finding been validated through re-audit?
    verified = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(String, nullable=False, default=_now_utc)
    updated_at = Column(String, nullable=False, default=_now_utc)

    # Relationships
    business = relationship("Business", backref="customer_findings")
    audit = relationship("Audit", backref="customer_findings")

    def mark_fixed(self) -> None:
        """Mark finding as fixed (awaiting verification)."""
        self.status = "fixed"
        self.updated_at = _now_utc()

    def mark_verified(self) -> None:
        """Mark finding as verified through re-audit."""
        self.status = "verified"
        self.verified = True
        self.updated_at = _now_utc()

    def reopen(self) -> None:
        """Reopen a finding (re-audit found it's still a problem)."""
        self.status = "open"
        self.verified = False
        self.updated_at = _now_utc()

    def __repr__(self) -> str:
        return (
            f"<CustomerFinding category={self.category!r} "
            f"status={self.status!r} severity={self.severity!r}>"
        )


# ---------------------------------------------------------------------------
# CompetitorRanking
# ---------------------------------------------------------------------------

class CompetitorRanking(Base):
    """
    Stores position/ranking data for a business relative to competitors.

    This is the data behind "YOUR CURRENT POSITION: #7 of 11 — for now"

    Each row represents one competitor's position for a specific
    audit in a specific market/service area.

    If Google rankings and AI results are measured separately,
    they should be stored as separate ranking_type entries.
    """
    __tablename__ = "competitor_ranking"

    id = Column(String, primary_key=True, default=_new_uuid)
    audit_id = Column(
        String,
        ForeignKey("audit.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_id = Column(
        String,
        ForeignKey("business.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "google" or "ai" — separate ranking types
    ranking_type = Column(String, nullable=False, default="google")

    # The market/service being compared
    market = Column(String, nullable=True)
    service_area = Column(String, nullable=True)

    # Competitor info
    competitor_name = Column(String, nullable=False)
    competitor_website = Column(String, nullable=True)
    position = Column(Integer, nullable=False)

    # Is this the audited business?
    is_subject = Column(Boolean, nullable=False, default=False)

    # Total competitors in this ranking
    total_competitors = Column(Integer, nullable=False)

    created_at = Column(String, nullable=False, default=_now_utc)

    # Relationships
    business = relationship("Business", backref="competitor_rankings")
    audit = relationship("Audit", backref="competitor_rankings")

    def __repr__(self) -> str:
        return (
            f"<CompetitorRanking #{self.position} "
            f"{self.competitor_name!r} is_subject={self.is_subject}>"
        )


# ---------------------------------------------------------------------------
# CompetitorEvidence
# ---------------------------------------------------------------------------

class CompetitorEvidence(Base):
    """
    Evidence of what a competitor is doing better than the audited business.

    Only store verified evidence — never claim a competitor is better
    without evidence supporting that statement.
    """
    __tablename__ = "competitor_evidence"

    id = Column(String, primary_key=True, default=_new_uuid)
    audit_id = Column(
        String,
        ForeignKey("audit.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_id = Column(
        String,
        ForeignKey("business.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Which competitor this evidence is about
    competitor_name = Column(String, nullable=False)

    # What the competitor is doing better
    evidence_summary = Column(Text, nullable=False)

    # Which category this relates to
    category = Column(String, nullable=True)

    # Source where this was observed
    source_url = Column(String, nullable=True)

    created_at = Column(String, nullable=False, default=_now_utc)

    # Relationships
    business = relationship("Business", backref="competitor_evidence")
    audit = relationship("Audit", backref="competitor_evidence")

    def __repr__(self) -> str:
        return (
            f"<CompetitorEvidence competitor={self.competitor_name!r} "
            f"category={self.category!r}>"
        )


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

# Fetch customer findings by audit and category
Index(
    "ix_customer_finding_audit_category",
    CustomerFinding.audit_id,
    CustomerFinding.category,
)

# Fetch customer findings by business and status
Index(
    "ix_customer_finding_business_status",
    CustomerFinding.business_id,
    CustomerFinding.status,
)

# Fetch competitor rankings by audit
Index(
    "ix_competitor_ranking_audit",
    CompetitorRanking.audit_id,
    CompetitorRanking.ranking_type,
)

# Fetch competitor evidence by audit
Index(
    "ix_competitor_evidence_audit",
    CompetitorEvidence.audit_id,
    CompetitorEvidence.competitor_name,
)
