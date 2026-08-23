"""
Zero to GEO — Pydantic request/response schemas.

Schemas are separate from ORM models (see ADR-007).
Request schemas validate incoming data.
Response schemas define the JSON shape sent to clients.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, field_validator, model_validator
import re


# ---------------------------------------------------------------------------
# Shared / enums
# ---------------------------------------------------------------------------

VALID_SEVERITIES = {"critical", "high", "medium", "low", "positive"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_STATUSES = {"pending", "crawling", "extracting", "analyzing", "scoring", "complete", "failed"}

PILLAR_DISPLAY_NAMES = {
    "entity_clarity": "Business Entity Clarity",
    "local_signals": "Local / NAP Signals",
    "structured_data": "Structured Data",
    "content": "Content / Answerability",
    "authority": "Authority / Trust",
    "citation_readiness": "AI Citation Readiness",
}


# ---------------------------------------------------------------------------
# Business schemas
# ---------------------------------------------------------------------------

class BusinessCreate(BaseModel):
    """Input schema for creating a new audit (and business record)."""
    business_name: str
    website_url: str
    city: str
    state: str
    category: str

    @field_validator("business_name")
    @classmethod
    def business_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Business name cannot be empty.")
        if len(v) > 200:
            raise ValueError("Business name must be 200 characters or fewer.")
        return v

    @field_validator("website_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Website URL cannot be empty.")
        # Prepend https:// if no scheme provided
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        # Basic URL structure check
        url_pattern = re.compile(
            r'^https?://'
            r'(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)'
            r'+[A-Za-z]{2,}',
            re.IGNORECASE,
        )
        if not url_pattern.match(v):
            raise ValueError("Please enter a valid website URL (e.g. https://example.com).")
        if len(v) > 500:
            raise ValueError("Website URL must be 500 characters or fewer.")
        return v

    @field_validator("city")
    @classmethod
    def city_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("City cannot be empty.")
        return v

    @field_validator("state")
    @classmethod
    def state_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("State cannot be empty.")
        return v

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category cannot be empty.")
        return v


class BusinessResponse(BaseModel):
    """Business record as returned in API responses."""
    id: str
    name: str
    website: str
    city: str
    state: str
    category: str
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# PillarResult schemas
# ---------------------------------------------------------------------------

class PillarResultResponse(BaseModel):
    """Score and summary for one GEO pillar."""
    id: str
    audit_id: str
    pillar: str
    pillar_display: str   # Human-readable name
    score: float
    summary: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_display(cls, obj) -> "PillarResultResponse":
        return cls(
            id=obj.id,
            audit_id=obj.audit_id,
            pillar=obj.pillar,
            pillar_display=PILLAR_DISPLAY_NAMES.get(obj.pillar, obj.pillar),
            score=obj.score,
            summary=obj.summary,
        )


# ---------------------------------------------------------------------------
# Finding schemas
# ---------------------------------------------------------------------------

class FindingResponse(BaseModel):
    """One finding within a GEO audit."""
    id: str
    audit_id: str
    pillar: str
    pillar_display: str
    severity: str
    title: str
    finding: str
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    priority: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_display(cls, obj) -> "FindingResponse":
        return cls(
            id=obj.id,
            audit_id=obj.audit_id,
            pillar=obj.pillar,
            pillar_display=PILLAR_DISPLAY_NAMES.get(obj.pillar, obj.pillar),
            severity=obj.severity,
            title=obj.title,
            finding=obj.finding,
            evidence=obj.evidence,
            recommendation=obj.recommendation,
            priority=obj.priority,
        )


# ---------------------------------------------------------------------------
# Action plan item
# ---------------------------------------------------------------------------

class ActionPlanItem(BaseModel):
    """One item in the prioritized action plan."""
    priority: str   # P0|P1|P2|P3
    description: str
    pillar: str
    pillar_display: str


# ---------------------------------------------------------------------------
# Audit schemas
# ---------------------------------------------------------------------------

class AuditCreate(BaseModel):
    """Input for POST /api/audits — wraps BusinessCreate."""
    business_name: str
    website_url: str
    city: str
    state: str
    category: str

    @field_validator("business_name")
    @classmethod
    def business_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Business name cannot be empty.")
        return v

    @field_validator("website_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Website URL cannot be empty.")
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        url_pattern = re.compile(
            r'^https?://'
            r'(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)'
            r'+[A-Za-z]{2,}',
            re.IGNORECASE,
        )
        if not url_pattern.match(v):
            raise ValueError("Please enter a valid website URL (e.g. https://example.com).")
        return v

    @field_validator("city")
    @classmethod
    def city_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("City cannot be empty.")
        return v

    @field_validator("state")
    @classmethod
    def state_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("State cannot be empty.")
        return v

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category cannot be empty.")
        return v


class AuditStatusResponse(BaseModel):
    """
    Returned by GET /api/audits/{id}.
    Provides enough info for the frontend polling loop.
    """
    id: str
    status: str
    overall_score: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    business: BusinessResponse

    model_config = {"from_attributes": True}


class AuditReportResponse(BaseModel):
    """
    Full GEO report returned by GET /api/audits/{id}/report.
    Only available when audit status = complete.
    """
    id: str
    status: str
    overall_score: float
    classification: str       # Poor | Needs Work | Good Foundation | Strong | Excellent
    summary: str              # Executive summary (3-5 sentence description)
    created_at: str
    completed_at: Optional[str] = None
    business: BusinessResponse
    pillar_results: List[PillarResultResponse]
    findings: List[FindingResponse]
    action_plan: List[ActionPlanItem]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Error schema
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error response shape."""
    detail: str
