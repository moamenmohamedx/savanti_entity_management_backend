"""Taskade field ID to entity attribute mapping.

IMPORTANT: Update FIELD_MAP after running schema discovery.
Use: GET /api/entities/schema to see actual field IDs.
"""

from typing import Dict, List, Any

# Maps Taskade field handle → entity attribute name
# UPDATED with actual field IDs from Taskade schema
FIELD_MAP: Dict[str, str] = {
    "@e001": "entity_id",
    "@e002": "entity_name",
    "@e003": "entity_type",
    "@e004": "status",
    "@e005": "jurisdiction",
    "@e006": "formation_date",
    "@e007": "filing_id",
    "@e008": "ein",
    "@e009": "legal_address",
    "@e010": "legal_city",
    "@e011": "legal_state",
    "@e012": "legal_zip",
    "@e013": "mailing_address",
    "@e014": "mailing_city",
    "@e015": "mailing_state",
    "@e016": "mailing_zip",
    "@e019": "renewal_frequency",
    "@e020": "next_renewal_cost",
    "@e021": "parent_entity",
    "@e022": "registered_agent_id",
    "@e023": "notes",
    "@e026": "created_by",
    "@e027": "modified_by",
}

# Reverse mapping for convenience
ATTR_TO_FIELD: Dict[str, str] = {v: k for k, v in FIELD_MAP.items()}

# Fields needed for dashboard display
DASHBOARD_FIELDS: List[str] = [
    "entity_id",
    "entity_name",
    "entity_type",
    "status",
    "jurisdiction",
    "formation_date",
]


def get_dashboard_field_ids() -> List[str]:
    """Get Taskade field IDs needed for dashboard."""
    return [ATTR_TO_FIELD[attr] for attr in DASHBOARD_FIELDS if attr in ATTR_TO_FIELD]


def map_field_values(taskade_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Taskade field IDs to entity attribute names."""
    return {
        FIELD_MAP.get(field_id, field_id): value
        for field_id, value in taskade_data.items()
        if field_id in FIELD_MAP
    }

