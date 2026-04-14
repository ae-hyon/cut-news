"""Pytest configuration and fixtures."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client
