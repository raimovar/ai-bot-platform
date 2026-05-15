"""
Session model - conversation sessions.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Session(Base):
    """Chat session model - a conversation thread."""
    
    __tablename__ = "sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # External ID (e.g., Telegram chat_id, web session)
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    
    # Session type
    session_type: Mapped[str] = mapped_column(
        String(50),
        default="telegram"
    )  # telegram, web, api
    
    # User info
    user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Message count
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Token usage
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Custom metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Context snapshot (for quick retrieval without full history)
    context_snapshot: Mapped[str | None] = mapped_column(
        String(10000),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    bot = relationship("Bot", back_populates="sessions")
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    def __repr__(self) -> str:
        return f"<Session {self.id}>"
