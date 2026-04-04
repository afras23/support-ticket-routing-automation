"""
Shared test fixtures.

Sets DATABASE_URL to an in-memory SQLite database before the app is
imported so tests don't read or write the development tickets.db file.
"""

import os

# Must be set before any app module is imported. The audit layer uses a sync
# SQLAlchemy engine; an async URL (e.g. sqlite+aiosqlite) breaks at import time.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """A TestClient that reuses a single app instance across the test session."""
    with TestClient(app) as c:
        yield c
