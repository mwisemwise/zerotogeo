"""
Zero to GEO — Bulk CSV upload API endpoints.

Routes:
  POST /api/bulk/upload         Upload a CSV and create audits for all rows
  GET  /api/bulk/{batch_id}     Get batch status (progress of all audits)
"""

import csv
import io
import re
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Business, Audit, Batch, AuditBatch
from app.schemas.schemas import BusinessResponse, AuditStatusResponse
from app.services.pipeline import run_audit_pipeline

router = APIRouter()


def _validate_url(url: str) -> str:
    """Normalize and validate a URL. Returns normalized URL or raises ValueError."""
    url = url.strip()
    if not url:
        raise ValueError("URL is empty")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    url_pattern = re.compile(
        r'^https?://'
        r'(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)'
        r'+[A-Za-z]{2,}',
        re.IGNORECASE,
    )
    if not url_pattern.match(url):
        raise ValueError(f"Invalid URL: {url}")
    return url


# ---------------------------------------------------------------------------
# POST /api/bulk/upload — upload CSV and start audits
# ---------------------------------------------------------------------------

@router.post("/upload", status_code=202)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a CSV file to create multiple audits at once.

    Expected CSV columns (header row required):
      business_name, website_url, city, state, category

    Returns a batch ID and list of created audits.
    """
    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a .csv file.",
        )

    # Read and decode the file
    try:
        content = await file.read()
        text = content.decode("utf-8-sig")  # Handle BOM if present
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not read CSV file. Make sure it's a valid UTF-8 text file.",
        )

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))

    # Validate headers
    required_columns = {"business_name", "industry", "website"}
    optional_columns = {"address", "phone", "email", "website_host"}
    if not reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="CSV file is empty or has no header row.",
        )

    # Normalize header names (strip whitespace, lowercase)
    normalized_headers = {h.strip().lower().replace(" ", "_") for h in reader.fieldnames}
    missing = required_columns - normalized_headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {', '.join(sorted(missing))}. "
                   f"Required: business_name, industry, website",
        )

    # Create a header mapping (original -> normalized)
    header_map = {}
    for h in reader.fieldnames:
        normalized = h.strip().lower().replace(" ", "_")
        header_map[h] = normalized

    # Parse rows
    rows = []
    errors = []
    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        # Remap keys to normalized names
        normalized_row = {header_map[k]: v.strip() if v else "" for k, v in row.items()}

        # Validate required fields
        row_errors = []
        if not normalized_row.get("business_name"):
            row_errors.append("business_name is empty")
        if not normalized_row.get("industry"):
            row_errors.append("industry is empty")

        # Validate URL
        try:
            normalized_row["website"] = _validate_url(normalized_row.get("website", ""))
        except ValueError as e:
            row_errors.append(str(e))

        if row_errors:
            errors.append({"row": i, "errors": row_errors})
        else:
            rows.append(normalized_row)

    if not rows and errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid rows found in CSV.",
                "row_errors": errors[:20],  # Limit error output
            },
        )

    if not rows and not errors:
        raise HTTPException(
            status_code=400,
            detail="CSV file has no data rows.",
        )

    # Create batch
    batch = Batch(total_audits=len(rows))
    db.add(batch)
    db.flush()

    # Create audits for each valid row
    created_audits = []
    for row in rows:
        # Parse city/state from address if provided
        address = row.get("address", "")
        city = ""
        state = ""
        if address:
            # Try to extract city and state from address
            # Common format: "123 Main St, City ST 12345" or "City, ST"
            import re as _re
            # Look for state abbreviation pattern
            state_match = _re.search(r'\b([A-Z]{2})\b', address)
            if state_match:
                state = state_match.group(1)
            # Try to get city from comma-separated parts
            parts = [p.strip() for p in address.split(",")]
            if len(parts) >= 2:
                # City is usually the second-to-last part before state/zip
                city_part = parts[-1].strip() if len(parts) == 2 else parts[1].strip()
                # Remove state and zip from city part
                city = _re.sub(r'\b[A-Z]{2}\b', '', city_part)
                city = _re.sub(r'\b\d{5}(-\d{4})?\b', '', city)
                city = city.strip()

        business = Business(
            name=row["business_name"],
            website=row["website"],
            city=city or "N/A",
            state=state or "N/A",
            category=row.get("industry", ""),
        )
        db.add(business)
        db.flush()

        audit = Audit(business_id=business.id)
        db.add(audit)
        db.flush()

        # Link audit to batch
        audit_batch = AuditBatch(batch_id=batch.id, audit_id=audit.id)
        db.add(audit_batch)

        created_audits.append({
            "audit_id": audit.id,
            "business_name": business.name,
            "website_url": business.website,
            "industry": row.get("industry", ""),
            "address": address,
            "phone": row.get("phone", ""),
            "email": row.get("email", ""),
            "website_host": row.get("website_host", ""),
        })

    db.commit()

    # Start pipelines for all audits in background threads
    import threading
    for audit_info in created_audits:
        thread = threading.Thread(
            target=run_audit_pipeline,
            args=(audit_info["audit_id"],),
            daemon=True,
        )
        thread.start()

    return {
        "batch_id": batch.id,
        "total": len(rows),
        "created_audits": created_audits,
        "skipped_rows": errors[:20] if errors else [],
    }


# ---------------------------------------------------------------------------
# GET /api/bulk/{batch_id} — batch status
# ---------------------------------------------------------------------------

@router.get("/{batch_id}")
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """
    Get the status of a bulk upload batch.

    Returns overall progress and status of each audit in the batch.
    """
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    # Get all audits in this batch
    audit_batches = batch.audit_batches
    audits = []
    completed = 0
    failed = 0

    for ab in audit_batches:
        audit = ab.audit
        business = audit.business
        audits.append({
            "audit_id": audit.id,
            "business_name": business.name,
            "website_url": business.website,
            "city": business.city,
            "state": business.state,
            "category": business.category,
            "status": audit.status,
            "overall_score": audit.overall_score,
            "error_message": audit.error_message,
        })
        if audit.status == "complete":
            completed += 1
        elif audit.status == "failed":
            failed += 1

    total = len(audits)
    in_progress = total - completed - failed
    batch_status = "complete" if in_progress == 0 else "processing"

    return {
        "batch_id": batch.id,
        "status": batch_status,
        "total": total,
        "completed": completed,
        "failed": failed,
        "in_progress": in_progress,
        "created_at": batch.created_at,
        "audits": audits,
    }
