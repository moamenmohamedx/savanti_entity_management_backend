"""Entity service for managing legal entities via Taskade backend."""

from datetime import datetime
from typing import Optional, Any
import base64
import time
import re
import structlog

from taskade import TaskadeClient, get_taskade_client
from entities.models import (
    Entity, EntityCreate, EntityUpdate, SyncResult, EntityDiscrepancy,
    DashboardStats, EntitySummary, CacheMetadata, DashboardResponse
)
from entities.cache import get_dashboard_cache
from entities.field_mapper import get_dashboard_field_ids, map_field_values

logger = structlog.get_logger()


class EntityService:
    """Service for managing legal entities stored in Taskade."""

    def __init__(self, taskade: TaskadeClient):
        self.taskade = taskade
        self.project_id = taskade.project_entities

    async def get_all(self) -> list[Entity]:
        """Retrieve all entities from Taskade."""
        tasks = await self.taskade.get_tasks(self.project_id)
        entities = []
        for task in tasks:
            entity = self._parse_task_to_entity(task)
            if entity:
                entities.append(entity)
        return entities

    async def get_by_id(self, entity_id: str) -> Optional[Entity]:
        """Get a specific entity by its ID."""
        entities = await self.get_all()
        for entity in entities:
            if entity.entity_id == entity_id:
                return entity
        return None

    async def search(self, query: str) -> list[Entity]:
        """Search entities by name, filing ID, or jurisdiction."""
        entities = await self.get_all()
        lower_query = query.lower()

        return [
            entity for entity in entities
            if (
                lower_query in entity.entity_name.lower() or
                (entity.filing_id and lower_query in entity.filing_id.lower()) or
                lower_query in entity.jurisdiction.lower()
            )
        ]

    async def create(self, entity_input: EntityCreate) -> Entity:
        """Create a new entity in Taskade."""
        # Generate unique entity_id
        timestamp_b36 = base64.b32encode(
            int(time.time() * 1000).to_bytes(8, 'big')
        ).decode().rstrip('=')[:8].upper()
        entity_id = f"ENT-{timestamp_b36}"

        # Create entity with ID
        entity_data = entity_input.model_dump()
        entity_data["entity_id"] = entity_id
        entity_data["created_date"] = datetime.utcnow().isoformat()
        entity_data["modified_date"] = datetime.utcnow().isoformat()

        # Convert to markdown
        content = self._entity_to_markdown(entity_data)

        # Create task in Taskade
        task = await self.taskade.create_task(self.project_id, content)

        # Build Entity object
        entity_data["taskade_task_id"] = task.get("id", "")
        logger.info("entity_created", entity_id=entity_id)

        # Invalidate dashboard cache
        cache = get_dashboard_cache()
        await cache.invalidate()

        return Entity(**entity_data)

    async def update(self, entity_id: str, updates: EntityUpdate) -> Entity:
        """Update an existing entity."""
        existing = await self.get_by_id(entity_id)
        if not existing:
            raise ValueError(f"Entity not found: {entity_id}")

        # Merge updates with existing data
        update_data = updates.model_dump(exclude_unset=True)
        merged_data = existing.model_dump()
        merged_data.update(update_data)
        merged_data["modified_date"] = datetime.utcnow().isoformat()

        # Convert to markdown
        content = self._entity_to_markdown(merged_data)

        # Update task in Taskade
        await self.taskade.update_task(
            self.project_id,
            existing.taskade_task_id,
            content
        )

        logger.info("entity_updated", entity_id=entity_id)

        # Invalidate dashboard cache
        cache = get_dashboard_cache()
        await cache.invalidate()

        return Entity(**merged_data)

    async def delete(self, entity_id: str) -> None:
        """Delete an entity."""
        existing = await self.get_by_id(entity_id)
        if not existing:
            raise ValueError(f"Entity not found: {entity_id}")

        await self.taskade.delete_task(self.project_id, existing.taskade_task_id)
        logger.info("entity_deleted", entity_id=entity_id)

        # Invalidate dashboard cache
        cache = get_dashboard_cache()
        await cache.invalidate()

    async def sync_with_state(self, entity_id: str) -> SyncResult:
        """Sync entity data with state secretary of state website."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")

        if not entity.filing_id:
            raise ValueError(f"Entity {entity_id} has no filing ID")

        # Import scraper dynamically
        from scrapers import get_scraper

        scraper = get_scraper(entity.jurisdiction)
        state_data = await scraper.search_by_filing_id(entity.filing_id)

        # Compare and identify discrepancies
        discrepancies = self._compare_entity_data(entity, state_data)

        return SyncResult(
            entity_id=entity_id,
            state_data=state_data,
            discrepancies=discrepancies,
            synced_at=datetime.utcnow().isoformat()
        )

    def _parse_task_to_entity(self, task: dict[str, Any]) -> Optional[Entity]:
        """Parse Taskade task to Entity object from markdown content."""
        content = task.get("text", "")
        if not content:
            return None

        # Extract entity data from markdown
        entity_data = {"taskade_task_id": task.get("id", "")}

        # Extract entity_id
        match = re.search(r'\*\*Entity ID\*\*:\s*(.+)', content)
        if match:
            entity_data["entity_id"] = match.group(1).strip()
        else:
            return None  # Skip tasks without entity_id

        # Extract other fields
        patterns = {
            "entity_name": r'^#\s+(.+)',
            "entity_type": r'\*\*Type\*\*:\s*(.+)',
            "status": r'\*\*Status\*\*:\s*(.+)',
            "jurisdiction": r'\*\*Jurisdiction\*\*:\s*(.+)',
            "formation_date": r'\*\*Formation Date\*\*:\s*(.+)',
            "filing_id": r'\*\*Filing ID\*\*:\s*(.+)',
            "ein": r'\*\*EIN\*\*:\s*(.+)',
            "legal_address": r'\*\*Legal Address\*\*:\s*(.+)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                value = match.group(1).strip()
                if value and value != "N/A":
                    entity_data[field] = value

        # Extract notes section
        notes_match = re.search(r'##\s+Notes\s*\n(.+)', content, re.DOTALL)
        if notes_match:
            notes = notes_match.group(1).strip()
            if notes and notes != "No additional notes":
                entity_data["notes"] = notes

        # Try to create Entity
        try:
            return Entity(**entity_data)
        except Exception as e:
            logger.warning("failed_to_parse_task", task_id=task.get("id"), error=str(e))
            return None

    def _entity_to_markdown(self, entity: dict[str, Any]) -> str:
        """Convert entity data to markdown format for Taskade storage."""
        return f"""# {entity.get('entity_name', 'Unnamed Entity')}

## Basic Information
- **Entity ID**: {entity.get('entity_id', 'N/A')}
- **Type**: {entity.get('entity_type', 'N/A')}
- **Status**: {entity.get('status', 'N/A')}
- **Jurisdiction**: {entity.get('jurisdiction', 'N/A')}
- **Formation Date**: {entity.get('formation_date', 'N/A')}
- **Filing ID**: {entity.get('filing_id', 'N/A')}
- **EIN**: {entity.get('ein', 'N/A')}

## Addresses
**Legal Address**: {entity.get('legal_address', 'N/A')}, {entity.get('legal_city', 'N/A')}, {entity.get('legal_state', 'N/A')} {entity.get('legal_zip', 'N/A')}

## Notes
{entity.get('notes', 'No additional notes')}
"""

    def _compare_entity_data(self, entity: Entity, state_data: dict) -> list[EntityDiscrepancy]:
        """Compare local entity data with state portal data."""
        discrepancies = []

        field_mappings = [
            ("entity_name", "entity_name"),
            ("status", "status"),
            ("formation_date", "formation_date"),
        ]

        for local_field, state_field in field_mappings:
            local_value = getattr(entity, local_field, None)
            state_value = state_data.get(state_field)

            if local_value and state_value and str(local_value) != str(state_value):
                discrepancies.append(EntityDiscrepancy(
                    field=local_field,
                    local_value=str(local_value),
                    state_value=str(state_value)
                ))

        return discrepancies

    async def get_dashboard(self, force_refresh: bool = False) -> DashboardResponse:
        """Get dashboard data (cached or fresh)."""
        cache = get_dashboard_cache()

        # Return cached data if valid and not forcing refresh
        if not force_refresh and cache.is_valid:
            cached_data = await cache.get()
            if cached_data:
                logger.info("dashboard_served_from_cache")
                return cached_data

        # Fetch fresh data
        dashboard = await self._fetch_dashboard_data()

        # Update cache
        await cache.set(dashboard)

        return dashboard

    async def refresh_dashboard(self) -> DashboardResponse:
        """Force refresh dashboard from Taskade."""
        logger.info("dashboard_force_refresh")
        cache = get_dashboard_cache()
        await cache.invalidate()
        return await self.get_dashboard(force_refresh=True)

    async def _fetch_dashboard_data(self) -> DashboardResponse:
        """Fetch all entity data using fan-out pattern."""
        field_ids = get_dashboard_field_ids()

        # Fan-out fetch
        raw_data = await self.taskade.fetch_all_entities_with_fields(
            self.project_id,
            field_ids
        )

        # Transform to EntitySummary objects
        entities = []
        for item in raw_data:
            mapped = map_field_values(item.get("fields", {}))
            try:
                entity = EntitySummary(
                    entity_id=mapped.get("entity_id", item.get("task_id", "")),
                    entity_name=mapped.get("entity_name", item.get("task_name", "Unknown")),
                    entity_type=mapped.get("entity_type", "Unknown"),
                    status=mapped.get("status", "Unknown"),
                    jurisdiction=mapped.get("jurisdiction", "Unknown"),
                    formation_date=mapped.get("formation_date"),
                    filing_id=mapped.get("filing_id"),
                    ein=mapped.get("ein"),
                    legal_address=mapped.get("legal_address"),
                    legal_city=mapped.get("legal_city"),
                    legal_state=mapped.get("legal_state"),
                    legal_zip=mapped.get("legal_zip"),
                    mailing_address=mapped.get("mailing_address"),
                    mailing_city=mapped.get("mailing_city"),
                    mailing_state=mapped.get("mailing_state"),
                    mailing_zip=mapped.get("mailing_zip"),
                    renewal_frequency=mapped.get("renewal_frequency"),
                    next_renewal_cost=mapped.get("next_renewal_cost"),
                    parent_entity=mapped.get("parent_entity"),
                    registered_agent_id=mapped.get("registered_agent_id"),
                    notes=mapped.get("notes"),
                    created_by=mapped.get("created_by"),
                    modified_by=mapped.get("modified_by"),
                    taskade_task_id=item.get("task_id", "")
                )
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Failed to parse entity: {e}")

        # Calculate stats
        stats = DashboardStats(
            total=len(entities),
            active=sum(1 for e in entities if e.status == "Active"),
            inactive=sum(1 for e in entities if e.status == "Inactive"),
            pending=sum(1 for e in entities if e.status == "Pending Formation"),
            dissolved=sum(1 for e in entities if e.status == "Dissolved")
        )

        # Build cache metadata
        cache = get_dashboard_cache()
        cache_meta = CacheMetadata(
            cached_at=cache.cached_at.isoformat() if cache.cached_at else None,
            is_stale=cache.is_stale,
            ttl_remaining_seconds=cache.ttl_remaining
        )

        return DashboardResponse(stats=stats, entities=entities, cache=cache_meta)


# Dependency injection helper
async def get_entity_service() -> EntityService:
    """FastAPI dependency for EntityService."""
    async for taskade in get_taskade_client():
        service = EntityService(taskade)
        yield service

