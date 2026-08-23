"""
Zero to GEO — FastAPI application entry point.

Registers routers, CORS middleware, and startup/shutdown lifecycle events.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.api.health import router as health_router
from app.api.audits import router as audits_router

# Path to the frontend build
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    init_db()
    yield


# Also call init_db at import time as a safety net.
# This ensures tables exist even if lifespan doesn't fire (e.g., some test clients).
init_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI Visibility & Citation Audit Platform. "
            "Analyzes business websites for GEO (Generative Engine Optimization) readiness."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Routers ----
    app.include_router(health_router, prefix="/api")
    app.include_router(audits_router, prefix="/api/audits", tags=["audits"])

    # ---- Frontend static files ----
    if FRONTEND_DIST.exists():
        # Serve static assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="static-assets")

        # SPA fallback: serve index.html for all non-API routes
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            # Try to serve an existing file first
            file_path = FRONTEND_DIST / full_path
            if full_path and file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            # Otherwise serve index.html for client-side routing
            return FileResponse(FRONTEND_DIST / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        async def root():
            return {
                "app": settings.app_name,
                "version": settings.app_version,
                "docs": "/docs",
                "health": "/api/health",
            }

    return app


app = create_app()
