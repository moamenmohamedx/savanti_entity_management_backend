"""Entity API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from entities.models import Entity, EntityCreate, EntityUpdate, SyncResult, DashboardResponse
from entities.service import EntityService, get_entity_service

logger = structlog.get_logger()

router = APIRouter()


@router.get("/", response_model=list[Entity])
async def list_entities(
    query: Optional[str] = Query(None, description="Search query for entities"),
    service: EntityService = Depends(get_entity_service)
):
    """List all entities with optional search filter."""
    try:
        if query:
            entities = await service.search(query)
            logger.info("entities_searched", query=query, count=len(entities))
        else:
            entities = await service.get_all()
            logger.info("entities_listed", count=len(entities))
        return entities
    except Exception as e:
        logger.error("list_entities_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    service: EntityService = Depends(get_entity_service)
):
    """Get dashboard with stats and entity list (cached)."""
    try:
        dashboard = await service.get_dashboard()
        logger.info("dashboard_retrieved",
                   total=dashboard.stats.total,
                   from_cache=dashboard.cache.ttl_remaining_seconds > 0)
        return dashboard
    except Exception as e:
        logger.error("get_dashboard_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboard/refresh", response_model=DashboardResponse)
async def refresh_dashboard(
    service: EntityService = Depends(get_entity_service)
):
    """Force refresh dashboard data from Taskade."""
    try:
        dashboard = await service.refresh_dashboard()
        logger.info("dashboard_refreshed", total=dashboard.stats.total)
        return dashboard
    except Exception as e:
        logger.error("refresh_dashboard_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_schema(
    service: EntityService = Depends(get_entity_service)
):
    """Get Taskade field schema (for debugging/discovery)."""
    try:
        fields = await service.taskade.get_fields(service.project_id)
        logger.info("schema_retrieved", field_count=len(fields))
        return {"fields": fields}
    except Exception as e:
        logger.error("get_schema_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}", response_model=Entity)
async def get_entity(
    entity_id: str,
    service: EntityService = Depends(get_entity_service)
):
    """Get a specific entity by ID."""
    try:
        entity = await service.get_by_id(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
        logger.info("entity_retrieved", entity_id=entity_id)
        return entity
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_entity_failed", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Entity, status_code=201)
async def create_entity(
    entity: EntityCreate,
    service: EntityService = Depends(get_entity_service)
):
    """Create a new entity."""
    try:
        created_entity = await service.create(entity)
        logger.info("entity_created", entity_id=created_entity.entity_id)
        return created_entity
    except Exception as e:
        logger.error("create_entity_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{entity_id}", response_model=Entity)
async def update_entity(
    entity_id: str,
    updates: EntityUpdate,
    service: EntityService = Depends(get_entity_service)
):
    """Update an existing entity."""
    try:
        updated_entity = await service.update(entity_id, updates)
        logger.info("entity_updated", entity_id=entity_id)
        return updated_entity
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("update_entity_failed", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: str,
    service: EntityService = Depends(get_entity_service)
):
    """Delete an entity."""
    try:
        await service.delete(entity_id)
        logger.info("entity_deleted", entity_id=entity_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_entity_failed", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{entity_id}/sync", response_model=SyncResult)
async def sync_entity(
    entity_id: str,
    service: EntityService = Depends(get_entity_service)
):
    """Sync entity with state secretary of state portal."""
    try:
        sync_result = await service.sync_with_state(entity_id)
        logger.info("entity_synced", entity_id=entity_id, discrepancies=len(sync_result.discrepancies))
        return sync_result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("sync_entity_failed", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

