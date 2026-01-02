"""Entity data models."""

from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field

EntityType = Literal[
    "LLC", "Corporation", "S-Corp", "C-Corp",
    "Partnership", "LP", "LLP", "Trust", "Nonprofit"
]
EntityStatus = Literal[
    "Active", "Inactive", "Dissolved", "Pending Formation"
]


class EntityBase(BaseModel):
    """Base entity fields."""
    entity_name: str = Field(..., min_length=1, max_length=200)
    entity_type: EntityType
    jurisdiction: str = Field(..., min_length=2, max_length=2)
    status: EntityStatus = "Active"
    formation_date: Optional[date] = None
    filing_id: Optional[str] = None
    ein: Optional[str] = None
    legal_address: Optional[str] = None
    legal_city: Optional[str] = None
    legal_state: Optional[str] = None
    legal_zip: Optional[str] = None
    notes: Optional[str] = None


class EntityCreate(EntityBase):
    """Create entity request."""
    pass


class EntityUpdate(BaseModel):
    """Update entity request (all optional)."""
    entity_name: Optional[str] = None
    entity_type: Optional[EntityType] = None
    jurisdiction: Optional[str] = None
    status: Optional[EntityStatus] = None
    formation_date: Optional[date] = None
    filing_id: Optional[str] = None
    ein: Optional[str] = None
    legal_address: Optional[str] = None
    legal_city: Optional[str] = None
    legal_state: Optional[str] = None
    legal_zip: Optional[str] = None
    notes: Optional[str] = None


class Entity(EntityBase):
    """Full entity with system fields."""
    entity_id: str
    taskade_task_id: str
    created_date: Optional[str] = None
    modified_date: Optional[str] = None


class EntityDiscrepancy(BaseModel):
    """Difference between local and state data."""
    field: str
    local_value: str
    state_value: str


class SyncResult(BaseModel):
    """State portal sync result."""
    entity_id: str
    synced_at: str
    state_data: dict
    discrepancies: list[EntityDiscrepancy] = []


class DashboardStats(BaseModel):
    """Entity status counts for dashboard cards."""
    total: int = Field(..., ge=0)
    active: int = Field(..., ge=0)
    inactive: int = Field(..., ge=0)
    pending: int = Field(..., ge=0)
    dissolved: int = Field(..., ge=0)


class EntitySummary(BaseModel):
    """Lightweight entity for dashboard table."""
    entity_id: str
    entity_name: str
    entity_type: str = "Unknown"
    status: str = "Unknown"
    jurisdiction: str = "Unknown"
    formation_date: Optional[str] = None
    taskade_task_id: str


class CacheMetadata(BaseModel):
    """Cache status information."""
    cached_at: Optional[str] = None
    is_stale: bool = False
    ttl_remaining_seconds: int = 0


class DashboardResponse(BaseModel):
    """Complete dashboard data with stats and entities."""
    stats: DashboardStats
    entities: list[EntitySummary]
    cache: CacheMetadata
