"""
Health check endpoint.
Returns application status and version information.
"""

from fastapi import APIRouter
from datetime import datetime, timezone

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check. Returns 200 when the application is running.
    Used for liveness probes and smoke testing.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
