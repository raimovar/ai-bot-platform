"""
Message model - individual messages in a session.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Message(Base):
    """Message model - individual chat message."""
    
    __tablename__ = "messages"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Message role
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # system, user, assistant, tool
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Optional name (for tools or multi-user)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Model info
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Token usage
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Latency
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Tool calls (if any)
    tool_calls: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True
    )  # [{"id": "call_xxx", "name": "function", "args": {...}}]
    
    tool_result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )  # {"call_xxx": "result"}
    
    # Source
    source: Mapped[str] = mapped_column(
        String(50),
        default="telegram"
    )  # telegram, web, api
    
    # Message metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Feedback
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<Message {self.role}: {self.content[:50]}>"
    
    @property
    def total_tokens(self) -> int:
        return (self.input_tokens or 0) + (self.output_tokens or 0)
