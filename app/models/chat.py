"""Pydantic models for chat-related API requests and responses."""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class Message(BaseModel):
    """Data model for a single message in a chat history."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request model for the main chat endpoint."""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for the main chat endpoint."""

    response: str
    action_taken: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
