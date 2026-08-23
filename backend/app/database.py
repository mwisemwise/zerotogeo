"""
Zero to GEO — Database session management.

Provides:
  - Engine creation from DATABASE_URL config
  - Session factory
  - get_db() FastAPI dependency (yields a session per request)
  - init_db() for creating tables on startup
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings
from app.models.models import Base


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _make_engine():
    connect_args = {}

    if settings.database_url.startswith("sqlite"):
        # SQLite requires check_same_thread=False for FastAPI's threaded model.
        # Also enable WAL mode for better concurrent read performance.
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        # Pool settings appropriate for SQLite (single writer).
        # For PostgreSQL, remove pool_size tuning or set appropriately.
        echo=settings.app_debug,  # Log SQL when DEBUG=True
    )

    # Enable WAL mode and foreign key enforcement for SQLite.
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _make_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency. Yields a database session and ensures it is closed
    after the request completes, even if an exception is raised.

    Usage:
        @router.get("/something")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create all database tables if they do not exist.
    Called on application startup.

    In production with PostgreSQL, use Alembic migrations instead of
    calling this directly. For SQLite MVP, this is sufficient.
    """
    Base.metadata.create_all(bind=engine)
