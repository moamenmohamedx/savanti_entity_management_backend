"""Chat API routes."""

from fastapi import APIRouter, Depends, HTTPException
import structlog

from chat.models import ChatRequest, ChatResponse
from chat.agent import chat_with_agent
from entities.service import EntityService, get_entity_service

logger = structlog.get_logger()

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: EntityService = Depends(get_entity_service)
):
    """Send a message to the AI agent and get a response.
    
    The agent can:
    - Search for entities by name, jurisdiction, or filing ID
    - Get detailed information about specific entities
    - Answer questions about entity management
    """
    try:
        response = await chat_with_agent(request.message, service)
        logger.info("chat_completed", message_length=len(request.message))
        return ChatResponse(response=response)
    except Exception as e:
        logger.error("chat_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

