"""Pytest configuration and fixtures."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from main import app
from taskade import TaskadeClient
from entities.service import EntityService


@pytest.fixture
async def async_client():
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_taskade_client():
    """Mock TaskadeClient for testing."""
    client = MagicMock(spec=TaskadeClient)
    client.project_entities = "test-project-id"
    
    # Mock async methods
    client.get_tasks = AsyncMock(return_value=[])
    client.create_task = AsyncMock(return_value={"id": "task-123"})
    client.update_task = AsyncMock(return_value={"id": "task-123"})
    client.delete_task = AsyncMock()
    client.close = AsyncMock()
    
    return client


@pytest.fixture
def mock_entity_service(mock_taskade_client):
    """Mock EntityService with mock TaskadeClient."""
    return EntityService(mock_taskade_client)


@pytest.fixture
def sample_entity_data():
    """Sample entity data for testing."""
    return {
        "entity_name": "Test LLC",
        "entity_type": "LLC",
        "jurisdiction": "WY",
        "status": "Active",
        "formation_date": "2024-01-15",
        "filing_id": "2024-123456",
        "ein": "12-3456789",
        "legal_address": "123 Main St",
        "legal_city": "Cheyenne",
        "legal_state": "WY",
        "legal_zip": "82001",
        "notes": "Test entity"
    }

