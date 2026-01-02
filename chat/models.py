"""Chat data models."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Chat request from user."""
    message: str


class ChatResponse(BaseModel):
    """Chat response from AI agent."""
    response: str

