"""Tests for entity endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from entities.models import Entity


@pytest.mark.asyncio
async def test_list_entities_empty(async_client, mock_entity_service):
    """Test listing entities when none exist."""
    with patch('entities.routes.get_entity_service') as mock_dep:
        mock_dep.return_value = mock_entity_service
        mock_entity_service.get_all = AsyncMock(return_value=[])
        
        response = await async_client.get("/api/entities/")
        
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_create_entity_success(async_client, mock_entity_service, sample_entity_data):
    """Test creating a new entity."""
    # Mock the create method to return an Entity
    created_entity = Entity(
        entity_id="ENT-TEST123",
        taskade_task_id="task-123",
        **sample_entity_data
    )
    
    with patch('entities.routes.get_entity_service') as mock_dep:
        mock_dep.return_value = mock_entity_service
        mock_entity_service.create = AsyncMock(return_value=created_entity)
        
        response = await async_client.post("/api/entities/", json=sample_entity_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["entity_id"] == "ENT-TEST123"
        assert data["entity_name"] == sample_entity_data["entity_name"]


@pytest.mark.asyncio
async def test_get_entity_not_found(async_client, mock_entity_service):
    """Test getting a non-existent entity returns 404."""
    with patch('entities.routes.get_entity_service') as mock_dep:
        mock_dep.return_value = mock_entity_service
        mock_entity_service.get_by_id = AsyncMock(return_value=None)
        
        response = await async_client.get("/api/entities/ENT-NOTFOUND")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_search_entities(async_client, mock_entity_service, sample_entity_data):
    """Test searching entities."""
    entity = Entity(
        entity_id="ENT-TEST123",
        taskade_task_id="task-123",
        **sample_entity_data
    )
    
    with patch('entities.routes.get_entity_service') as mock_dep:
        mock_dep.return_value = mock_entity_service
        mock_entity_service.search = AsyncMock(return_value=[entity])
        
        response = await async_client.get("/api/entities/?query=Test")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["entity_name"] == "Test LLC"

