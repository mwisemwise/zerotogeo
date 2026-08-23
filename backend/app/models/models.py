"""
Zero to GEO — SQLAlchemy ORM models.

Tables:
  business      — the business being audited
  audit         — one audit run for a business
  pillar_result — score + summary for each of the six GEO pillars
  finding       — individual findings within an audit

Design notes:
- All primary keys are UUIDs (string) for portability.
- Timestamps are stored as UTC ISO-8601 strings (SQLite-compatible).
- Foreign keys are enforced; cascade deletes keep orphans from accumulating.
- The schema is intentionally simple — no unnecessary tables.
- PostgreSQL can be substituted by changing DATABASE_URL (see ADR-001).
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def _now_utc() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Business
# ---------------------------------------------------------------------------

class Business(Base):
    """
    Represents a business that has been submitted for a GEO audit.

    One business can have many audits over time.
    """
    __tablename__ = "business"

    id = Column(String, primary_key=True, default=_new_uuid)
    name = Column(String, nullable=False)
    website = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    category = Column(String, nullable=False)
    created_at = Column(String, nullable=False, default=_now_utc)

    # Relationships
    audits = relationship(
        "Audit",
        back_populates="business",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Business id={self.id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class Audit(Base):
    """
    One audit run for a business.

    status lifecycle:
      pending → crawling → extracting → analyzing → scoring → complete
                                                            ↘ failed

    overall_score is populated when status = complete.
    error_message is populated when status = failed.
    """
    __tablename__ = "audit"

    id = Column(String, primary_key=True, default=_new_uuid)
    business_id = Column(
        String,
        ForeignKey("business.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String, nullable=False, default="pending")
    overall_score = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(String, nullable=False, default=_now_utc)
    completed_at = Column(String, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="audits")
    pillar_results = relationship(
        "PillarResult",
        back_populates="audit",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="PillarResult.pillar",
    )
    findings = relationship(
        "Finding",
        back_populates="audit",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Finding.priority",
    )

    def mark_complete(self, score: float) -> None:
        self.overall_score = round(score, 2)
        self.status = "complete"
        self.completed_at = _now_utc()

    def mark_failed(self, reason: str) -> None:
        self.status = "failed"
        self.error_message = reason
        self.completed_at = _now_utc()

    def __repr__(self) -> str:
        return f"<Audit id={self.id!r} status={self.status!r} score={self.overall_score}>"


# ---------------------------------------------------------------------------
# PillarResult
# ---------------------------------------------------------------------------

class PillarResult(Base):
    """
    Score and summary for one of the six GEO pillars within an audit.

    pillar values (canonical names):
      entity_clarity
      local_signals
      structured_data
      content
      authority
      citation_readiness
    """
    __tablename__ = "pillar_result"

    id = Column(String, primary_key=True, default=_new_uuid)
    audit_id = Column(
        String,
        ForeignKey("audit.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pillar = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    summary = Column(Text, nullable=True)

    # Relationships
    audit = relationship("Audit", back_populates="pillar_results")

    def __repr__(self) -> str:
        return f"<PillarResult pillar={self.pillar!r} score={self.score}>"


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

class Finding(Base):
    """
    An individual finding within an audit.

    severity levels: critical | high | medium | low | positive
    priority levels: P0 | P1 | P2 | P3  (P0 = fix immediately)

    evidence MUST be populated with something the system actually observed.
    It must never be blank for non-positive findings.
    """
    __tablename__ = "finding"

    id = Column(String, primary_key=True, default=_new_uuid)
    audit_id = Column(
        String,
        ForeignKey("audit.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pillar = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # critical|high|medium|low|positive
    title = Column(String, nullable=False)
    finding = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)       # What the system actually observed
    recommendation = Column(Text, nullable=True)
    priority = Column(String, nullable=True)     # P0|P1|P2|P3

    # Relationships
    audit = relationship("Audit", back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding severity={self.severity!r} title={self.title!r}>"


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

# Composite index for quickly fetching all audits for a business
Index("ix_audit_business_created", Audit.business_id, Audit.created_at)

# Composite index for fetching findings by audit + severity
Index("ix_finding_audit_severity", Finding.audit_id, Finding.severity)

# Composite index for fetching pillar results by audit
Index("ix_pillar_audit", PillarResult.audit_id, PillarResult.pillar)
