"""
Bot model - AI bot configuration.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Numeric, Text, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.core.database import Base


class Bot(Base):
    """AI Bot configuration model."""
    
    __tablename__ = "bots"
    
    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Model Configuration
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # openai, anthropic, ollama, lmstudio, huggingface
    
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Generation Parameters
    temperature: Mapped[float] = mapped_column(Numeric(4, 2), default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    top_p: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    frequency_penalty: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    presence_penalty: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    
    # System Prompt
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Memory Configuration
    memory_type: Mapped[str] = mapped_column(
        String(50),
        default="short_term"
    )  # none, short_term, long_term, hybrid
    
    memory_config: Mapped[dict] = mapped_column(
        JSON,
        default=dict
    )  # {"window_size": 10, "召回数量": 5}
    
    # Tools Configuration
    tools_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Integration
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_bot_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_allowed_chats: Mapped[list] = mapped_column(
        ARRAY(String),
        default=list
    )  # Empty = allow all
    
    # Webhook
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Runtime Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="stopped"
    )  # stopped, starting, running, error
    
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Stats
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    
    # Branding
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    last_started: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    owner = relationship("User", back_populates="bots")
    tools = relationship("BotTool", back_populates="bot", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="bot", cascade="all, delete-orphan")
    knowledge_sources = relationship(
        "KnowledgeSource",
        back_populates="bot",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Bot {self.name}>"
    
    @property
    def is_running(self) -> bool:
        return self.status == "running" and self.is_active


class BotTool(Base):
    """Bot tool/extension configuration."""
    
    __tablename__ = "bot_tools"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False
    )
    
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Tool configuration (JSON)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Tool definition (OpenAI function schema)
    definition: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationships
    bot = relationship("Bot", back_populates="tools")
    
    def __repr__(self) -> str:
        return f"<BotTool {self.tool_name}>"
