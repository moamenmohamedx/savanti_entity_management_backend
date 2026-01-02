"""Taskade field ID to entity attribute mapping.

IMPORTANT: Update FIELD_MAP after running schema discovery.
Use: GET /api/entities/schema to see actual field IDs.
"""

from typing import Dict, List, Any, Optional

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
    "filing_id",
    "ein",
    "legal_address",
    "legal_city",
    "legal_state",
    "legal_zip",
    "mailing_address",
    "mailing_city",
    "mailing_state",
    "mailing_zip",
    "renewal_frequency",
    "next_renewal_cost",
    "parent_entity",
    "registered_agent_id",
    "notes",
    "created_by",
    "modified_by",
]


def get_dashboard_field_ids() -> List[str]:
    """Get Taskade field IDs needed for dashboard."""
    return [ATTR_TO_FIELD[attr] for attr in DASHBOARD_FIELDS if attr in ATTR_TO_FIELD]


def normalize_field_value(value: Any) -> Optional[str]:
    """Extract string value from Taskade field objects.
    
    Taskade returns field values as complex dicts for certain field types:
    - Select: {'type': 'Select', 'optionId': 'llc'}
    - DateTime: {'type': 'DateTime', 'date': '2020-03-15'}
    
    This function extracts the actual value as a string.
    """
    if value is None:
        return None
    
    # Handle dict/object fields
    if isinstance(value, dict):
        field_type = value.get('type')
        
        if field_type == 'Select':
            return value.get('optionId')
        
        if field_type == 'DateTime':
            return value.get('date')
        
        # Handle other dict types by converting to string
        return str(value)
    
    # Handle primitives
    if isinstance(value, str):
        return value
    
    if isinstance(value, (int, float)):
        return str(value)
    
    return str(value)


def map_field_values(taskade_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Taskade field IDs to entity attribute names and normalize values."""
    return {
        FIELD_MAP.get(field_id, field_id): normalize_field_value(value)
        for field_id, value in taskade_data.items()
        if field_id in FIELD_MAP
    }

