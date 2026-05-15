"""
Bot schemas for API validation.
"""
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ─────────────────────────────────────────────────────────────
# Tool Schemas
# ─────────────────────────────────────────────────────────────

class BotToolCreate(BaseModel):
    """Schema for creating a bot tool."""
    tool_name: str = Field(..., min_length=1, max_length=100)
    tool_type: str = Field(..., description="http, command, function, api")
    config: dict = Field(default_factory=dict)
    definition: Optional[dict] = None
    is_enabled: bool = True
    priority: int = 0


class BotToolUpdate(BaseModel):
    """Schema for updating a bot tool."""
    tool_name: Optional[str] = None
    tool_type: Optional[str] = None
    config: Optional[dict] = None
    definition: Optional[dict] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


class BotToolResponse(BaseModel):
    """Schema for bot tool response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    tool_name: str
    tool_type: str
    config: dict
    definition: Optional[dict] = None
    is_enabled: bool
    priority: int


# ─────────────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────────────

class BotCreate(BaseModel):
    """Schema for creating a new bot."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    
    # Model
    provider: str = Field(..., description="openai, anthropic, ollama, lmstudio")
    model_name: str = Field(..., max_length=255)
    
    # Parameters
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: int = Field(2048, ge=1, le=32000)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2)
    
    # Prompt
    system_prompt: str = Field(..., min_length=1)
    
    # Memory
    memory_type: str = "short_term"
    memory_config: dict = Field(default_factory=dict)
    
    # Telegram
    telegram_enabled: bool = False
    telegram_bot_name: Optional[str] = None
    telegram_allowed_chats: list[str] = Field(default_factory=list)
    
    # Branding
    avatar_url: Optional[str] = None
    welcome_message: Optional[str] = None
    
    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v, info):
        if v:
            return v.lower().replace(" ", "-")
        # Auto-generate from name
        name = info.data.get("name", "")
        return name.lower().replace(" ", "-")[:100]


class BotUpdate(BaseModel):
    """Schema for updating a bot."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    
    # Model
    provider: Optional[str] = None
    model_name: Optional[str] = None
    
    # Parameters
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2)
    
    # Prompt
    system_prompt: Optional[str] = None
    
    # Memory
    memory_type: Optional[str] = None
    memory_config: Optional[dict] = None
    
    # Telegram
    telegram_enabled: Optional[bool] = None
    telegram_bot_name: Optional[str] = None
    telegram_allowed_chats: Optional[list[str]] = None
    
    # Status
    is_active: Optional[bool] = None
    
    # Branding
    avatar_url: Optional[str] = None
    welcome_message: Optional[str] = None


class BotConfig(BaseModel):
    """Schema for bot runtime configuration."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    system_prompt: str
    memory_type: str
    memory_config: dict
    tools_enabled: bool
    telegram_enabled: bool
    telegram_token: Optional[str] = None
    telegram_bot_name: Optional[str] = None
    telegram_allowed_chats: list[str]


class BotStartRequest(BaseModel):
    """Schema for starting a bot."""
    telegram_token: Optional[str] = None


class BotStopRequest(BaseModel):
    """Schema for stopping a bot."""
    pass


# ─────────────────────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────────────────────

class BotResponse(BaseModel):
    """Schema for bot response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    owner_id: uuid.UUID
    is_public: bool
    is_active: bool
    
    # Model
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    
    # Prompt
    system_prompt: str
    
    # Memory
    memory_type: str
    memory_config: dict
    
    # Status
    status: str
    last_error: Optional[str] = None
    total_messages: int
    total_tokens_used: int
    
    # Telegram
    telegram_enabled: bool
    telegram_bot_name: Optional[str] = None
    
    # Branding
    avatar_url: Optional[str] = None
    welcome_message: Optional[str] = None
    
    # Metadata
    metadata: dict
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_started: Optional[datetime] = None
    
    # Computed
    tools: list[BotToolResponse] = []
    is_running: bool = False


class BotListResponse(BaseModel):
    """Schema for paginated bot list."""
    items: list[BotResponse]
    total: int
    page: int
    page_size: int
    pages: int


class BotStatsResponse(BaseModel):
    """Schema for bot statistics."""
    total_bots: int
    running_bots: int
    stopped_bots: int
    error_bots: int
    total_messages: int
    total_tokens: int


# ─────────────────────────────────────────────────────────────
# Telegram Schemas
# ─────────────────────────────────────────────────────────────

class BotTelegramConfig(BaseModel):
    """Schema for Telegram configuration."""
    telegram_token: str
    webhook_url: Optional[str] = None
    allowed_chats: list[int] = Field(default_factory=list)
    disallowed_chats: list[int] = Field(default_factory=list)
    allow_groups: bool = False
    allow_channels: bool = False
    bot_commands: list[dict] = Field(default_factory=list)


class TelegramBotInfo(BaseModel):
    """Schema for Telegram bot info."""
    id: int
    is_bot: bool
    username: str
    first_name: str
    last_name: Optional[str] = None


class WebhookInfoResponse(BaseModel):
    """Schema for webhook info."""
    url: Optional[str] = None
    has_custom_certificate: bool = False
    pending_update_count: int = 0
    last_error_message: Optional[str] = None
    max_connections: Optional[int] = None


class TelegramUpdateResponse(BaseModel):
    """Schema for processing a Telegram update."""
    ok: bool
    message_id: Optional[int] = None
    chat_id: Optional[int] = None


# ─────────────────────────────────────────────────────────────
# Session Schemas
# ─────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    """Schema for session response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bot_id: uuid.UUID
    external_id: str
    chat_type: str
    chat_title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str
    metadata: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Schema for message response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    metadata: dict
    created_at: datetime


class SessionCreate(BaseModel):
    """Schema for creating a session."""
    bot_id: uuid.UUID
    external_id: str
    chat_type: str = "private"
    chat_title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Runtime Schemas
# ─────────────────────────────────────────────────────────────

class RuntimeStatusResponse(BaseModel):
    """Schema for runtime status."""
    running: bool
    uptime_seconds: float
    total_bots: int
    running_bots: int
    error_bots: int
    bots: dict


class RuntimeBotStatus(BaseModel):
    """Schema for individual bot runtime status."""
    status: str
    messages_processed: int = 0
    messages_failed: int = 0
    avg_response_time: float = 0.0
    last_message_at: Optional[str] = None
    last_error: Optional[str] = None
