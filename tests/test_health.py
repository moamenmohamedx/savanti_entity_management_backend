"""Tests for health and root endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """Test health check endpoint returns healthy status."""
    response = await async_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "entity-management-backend"


@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    """Test root endpoint returns API information."""
    response = await async_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Entity Management API"
    assert data["version"] == "1.0.0"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"

