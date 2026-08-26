"""
Zero to GEO — Businesses/Prospects API endpoints.

Routes:
  GET  /api/businesses              List all businesses with latest audit info
  GET  /api/businesses/{id}         Get a single business with full audit history
  POST /api/businesses/import       Import businesses from JSON (dedup by website)
  POST /api/businesses/launch-audits  Launch audits for selected businesses
"""

import threading
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Business, Audit, Batch, AuditBatch
from app.services.pipeline import run_audit_pipeline

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------

class BusinessImportItem(BaseModel):
    """One business in an import request."""
    name: str
    website: str
    city: str
    state: str
    category: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Business name cannot be empty.")
        return v

    @field_validator("website")
    @classmethod
    def website_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Website cannot be empty.")
        return v


class BusinessImportRequest(BaseModel):
    """Request body for POST /api/businesses/import."""
    businesses: list[BusinessImportItem]


class LaunchAuditsRequest(BaseModel):
    """Request body for POST /api/businesses/launch-audits."""
    business_ids: list[str]

    @field_validator("business_ids")
    @classmethod
    def ids_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("business_ids cannot be empty.")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """
    Normalize a URL for deduplication.
    Strips protocol, lowercases hostname, strips trailing slash.
    """
    url = url.strip()
    if not url:
        return ""
    # Add scheme if missing so urlparse works correctly
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    # Lowercase the hostname, keep path
    hostname = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/")
    # Return without protocol for comparison
    return f"{hostname}{path}"


def _ensure_scheme(url: str) -> str:
    """Ensure a URL has a scheme. Adds https:// if missing."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


# ---------------------------------------------------------------------------
# GET /api/businesses — list all businesses with latest audit info
# ---------------------------------------------------------------------------

@router.get("")
def list_businesses(
    search: Optional[str] = Query(None, description="Filter by name, city, state, or category"),
    db: Session = Depends(get_db),
):
    """
    List all businesses with their latest audit info.
    Supports optional ?search= query param for filtering by name/city/state/category.
    Results are sorted by name.
    """
    query = db.query(Business)

    # Apply search filter if provided
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (Business.name.ilike(search_term))
            | (Business.city.ilike(search_term))
            | (Business.state.ilike(search_term))
            | (Business.category.ilike(search_term))
        )

    # Sort by name
    businesses = query.order_by(Business.name).all()

    results = []
    for biz in businesses:
        # Get all audits for this business, ordered newest first
        audits = (
            db.query(Audit)
            .filter(Audit.business_id == biz.id)
            .order_by(Audit.created_at.desc())
            .all()
        )

        # Build latest audit info
        latest_audit = None
        if audits:
            latest = audits[0]
            latest_audit = {
                "audit_id": latest.id,
                "status": latest.status,
                "overall_score": latest.overall_score,
                "completed_at": latest.completed_at,
            }

        results.append({
            "id": biz.id,
            "name": biz.name,
            "website": biz.website,
            "city": biz.city,
            "state": biz.state,
            "category": biz.category,
            "created_at": biz.created_at,
            "latest_audit": latest_audit,
            "audit_count": len(audits),
        })

    return results


# ---------------------------------------------------------------------------
# GET /api/businesses/{id} — single business with full audit history
# ---------------------------------------------------------------------------

@router.get("/{business_id}")
def get_business(business_id: str, db: Session = Depends(get_db)):
    """
    Get a single business with its full audit history.
    Audits are ordered newest-first.
    """
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")

    # Get all audits ordered newest first
    audits = (
        db.query(Audit)
        .filter(Audit.business_id == business.id)
        .order_by(Audit.created_at.desc())
        .all()
    )

    audit_list = [
        {
            "id": audit.id,
            "status": audit.status,
            "overall_score": audit.overall_score,
            "created_at": audit.created_at,
            "completed_at": audit.completed_at,
        }
        for audit in audits
    ]

    return {
        "id": business.id,
        "name": business.name,
        "website": business.website,
        "city": business.city,
        "state": business.state,
        "category": business.category,
        "created_at": business.created_at,
        "audits": audit_list,
    }


# ---------------------------------------------------------------------------
# POST /api/businesses/import — import businesses from JSON (dedup by URL)
# ---------------------------------------------------------------------------

@router.post("/import")
def import_businesses(
    payload: BusinessImportRequest,
    db: Session = Depends(get_db),
):
    """
    Import businesses from a JSON array.
    Deduplicates by normalized website URL (strips protocol, lowercases hostname,
    strips trailing slash).
    """
    if not payload.businesses:
        raise HTTPException(status_code=400, detail="No businesses provided.")

    # Get all existing business website URLs for dedup
    existing_businesses = db.query(Business).all()
    existing_urls = {_normalize_url(b.website) for b in existing_businesses}

    imported = []
    duplicates = 0
    seen_in_batch: set[str] = set()  # Track duplicates within the same import

    for item in payload.businesses:
        normalized = _normalize_url(item.website)

        # Skip if already exists in DB or already seen in this batch
        if normalized in existing_urls or normalized in seen_in_batch:
            duplicates += 1
            continue

        seen_in_batch.add(normalized)

        business = Business(
            name=item.name.strip(),
            website=_ensure_scheme(item.website),
            city=item.city.strip(),
            state=item.state.strip(),
            category=item.category.strip(),
        )
        db.add(business)
        db.flush()

        imported.append({
            "id": business.id,
            "name": business.name,
            "website": business.website,
            "city": business.city,
            "state": business.state,
            "category": business.category,
            "created_at": business.created_at,
        })

    db.commit()

    return {
        "imported": len(imported),
        "duplicates": duplicates,
        "businesses": imported,
    }


# ---------------------------------------------------------------------------
# POST /api/businesses/launch-audits — launch audits for selected businesses
# ---------------------------------------------------------------------------

@router.post("/launch-audits", status_code=202)
def launch_audits(
    payload: LaunchAuditsRequest,
    db: Session = Depends(get_db),
):
    """
    Launch audits for selected businesses.
    Creates a Batch, creates Audit records for each business, links them via AuditBatch,
    and starts run_audit_pipeline in background threads (same pattern as bulk.py).
    """
    # Validate that all business IDs exist
    businesses = []
    for bid in payload.business_ids:
        business = db.get(Business, bid)
        if not business:
            raise HTTPException(
                status_code=404,
                detail=f"Business not found: {bid}",
            )
        businesses.append(business)

    # Create batch
    batch = Batch(total_audits=len(businesses))
    db.add(batch)
    db.flush()

    # Create audits and link to batch
    created_audits = []
    for business in businesses:
        audit = Audit(business_id=business.id)
        db.add(audit)
        db.flush()

        # Link audit to batch
        audit_batch = AuditBatch(batch_id=batch.id, audit_id=audit.id)
        db.add(audit_batch)

        created_audits.append({
            "audit_id": audit.id,
            "business_id": business.id,
            "business_name": business.name,
        })

    db.commit()

    # Start pipelines in background threads (same pattern as bulk.py)
    for audit_info in created_audits:
        thread = threading.Thread(
            target=run_audit_pipeline,
            args=(audit_info["audit_id"],),
            daemon=True,
        )
        thread.start()

    return {
        "batch_id": batch.id,
        "total": len(created_audits),
        "audits": created_audits,
    }
