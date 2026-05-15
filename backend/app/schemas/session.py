"""
Session and Message schemas for API validation.
"""
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────────────────────────────────────────
# Message Schemas
# ─────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    """Schema for creating a message (internal)."""
    role: str
    content: str
    name: Optional[str] = None
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    tool_calls: Optional[list[dict]] = None
    tool_result: Optional[dict] = None
    source: str = "api"
    metadata: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Schema for message response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    name: Optional[str] = None
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    tool_calls: Optional[list[dict]] = None
    tool_result: Optional[dict] = None
    source: str
    metadata: dict
    rating: Optional[int] = None
    created_at: datetime
    
    @property
    def total_tokens(self) -> int:
        return (self.input_tokens or 0) + (self.output_tokens or 0)


class MessageFeedback(BaseModel):
    """Schema for rating a message."""
    rating: int = Field(..., ge=1, le=5)


class MessageListResponse(BaseModel):
    """Schema for paginated message list."""
    items: list[MessageResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ─────────────────────────────────────────────────────────────
# Session Schemas
# ─────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """Schema for creating a session."""
    bot_id: uuid.UUID
    external_id: Optional[str] = None
    session_type: str = "telegram"
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    """Schema for updating a session."""
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class SessionResponse(BaseModel):
    """Schema for session response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    bot_id: uuid.UUID
    external_id: Optional[str] = None
    session_type: str
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    is_active: bool
    message_count: int
    total_tokens: int
    metadata: dict
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    
    # Include recent messages
    recent_messages: list[MessageResponse] = []


class SessionListResponse(BaseModel):
    """Schema for paginated session list."""
    items: list[SessionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ─────────────────────────────────────────────────────────────
# Chat Request/Response
# ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Schema for sending a chat message."""
    bot_id: uuid.UUID
    message: str
    session_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Schema for chat response."""
    session_id: uuid.UUID
    message_id: uuid.UUID
    response: str
    model: str
    tokens_used: int
    latency_ms: int
    session: SessionResponse
