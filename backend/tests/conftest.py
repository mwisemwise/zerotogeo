"""
Shared pytest configuration for all backend tests.

Sets up a single test database and overrides the FastAPI get_db dependency
so all tests use the same isolated test database.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models.models import Base

TEST_DATABASE_URL = "sqlite:///./test_zero_to_geo.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply the override once at module load
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_test_db():
    """Drop and recreate all tables before each test for full isolation."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    """Yield a test database session."""
    session = TestSessionLocal()
    yield session
    session.close()
