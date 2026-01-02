"""Entity Management AI Agent using Pydantic AI."""

import os
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
import structlog

from config import get_settings
from entities.service import EntityService

logger = structlog.get_logger()


@dataclass
class AgentDeps:
    """Dependencies for the AI agent."""
    entity_service: EntityService


# Load settings and expose OPENROUTER_API_KEY to os.environ
# (Pydantic Settings reads .env but doesn't populate os.environ, which Pydantic AI requires)
settings = get_settings()
os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key.get_secret_value()

# Create agent with OpenRouter
agent = Agent(
    f'openrouter:{settings.default_model}',
    deps_type=AgentDeps,
    retries=2,
)


# System instructions
agent.instructions = """You are an expert entity management assistant helping users manage legal entities.

Your capabilities:
- Search for entities by name, jurisdiction, or filing ID
- Get detailed information about specific entities
- Answer questions about entity status, formation dates, and addresses
- Provide guidance on entity compliance and state requirements

Be concise, accurate, and helpful. When users ask about entities, use the available tools to search and retrieve data from the database.
"""


@agent.tool
async def search_entities(ctx: RunContext[AgentDeps], query: str) -> str:
    """Search for entities by name, jurisdiction, or filing ID.
    
    Args:
        query: Search term (entity name, jurisdiction code, or filing ID)
        
    Returns:
        List of matching entities with their basic information
    """
    try:
        entities = await ctx.deps.entity_service.search(query)
        if not entities:
            return f"No entities found matching '{query}'"
        
        results = []
        for entity in entities:
            results.append(
                f"- {entity.entity_name} (ID: {entity.entity_id})\n"
                f"  Type: {entity.entity_type}, Status: {entity.status}, "
                f"Jurisdiction: {entity.jurisdiction}"
            )
        
        return f"Found {len(entities)} entities:\n" + "\n".join(results)
    except Exception as e:
        logger.error("search_entities_tool_failed", error=str(e))
        return f"Error searching entities: {str(e)}"


@agent.tool
async def get_entity_details(ctx: RunContext[AgentDeps], entity_id: str) -> str:
    """Get detailed information about a specific entity.
    
    Args:
        entity_id: The unique entity ID (format: ENT-XXXXXXXX)
        
    Returns:
        Complete entity details including addresses and notes
    """
    try:
        entity = await ctx.deps.entity_service.get_by_id(entity_id)
        if not entity:
            return f"Entity not found: {entity_id}"
        
        details = f"""Entity Details for {entity.entity_name}:
- Entity ID: {entity.entity_id}
- Type: {entity.entity_type}
- Status: {entity.status}
- Jurisdiction: {entity.jurisdiction}
- Formation Date: {entity.formation_date or 'N/A'}
- Filing ID: {entity.filing_id or 'N/A'}
- EIN: {entity.ein or 'N/A'}

Address:
{entity.legal_address or 'N/A'}, {entity.legal_city or 'N/A'}, {entity.legal_state or 'N/A'} {entity.legal_zip or 'N/A'}
"""
        
        if entity.notes:
            details += f"\nNotes:\n{entity.notes}"
        
        return details
    except Exception as e:
        logger.error("get_entity_details_tool_failed", entity_id=entity_id, error=str(e))
        return f"Error retrieving entity details: {str(e)}"


@agent.tool_plain
def get_supported_entity_types() -> str:
    """Get list of supported entity types.
    
    Returns:
        List of valid entity types that can be created
    """
    return """Supported entity types:
- LLC (Limited Liability Company)
- Corporation
- S-Corp (S Corporation)
- C-Corp (C Corporation)
- Partnership
- LP (Limited Partnership)
- LLP (Limited Liability Partnership)
- Trust
- Nonprofit"""


async def chat_with_agent(message: str, entity_service: EntityService) -> str:
    """Run the AI agent with a user message.
    
    Args:
        message: User's message/question
        entity_service: EntityService instance for database access
        
    Returns:
        AI agent's response
    """
    deps = AgentDeps(entity_service=entity_service)
    
    try:
        result = await agent.run(message, deps=deps)
        return result.data
    except Exception as e:
        logger.error("agent_run_failed", error=str(e))
        return f"I encountered an error processing your request: {str(e)}"

