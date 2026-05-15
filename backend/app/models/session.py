"""
Session model for chat sessions.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class Session(Base):
    """Chat session model."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)

    # External ID (e.g., Telegram chat_id)
    external_id = Column(String(255), nullable=False)

    # Chat info
    chat_type = Column(String(50), default="private")
    chat_title = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)

    # Configuration
    config = Column(JSONB, default=dict)
    message_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    bot = relationship("Bot", back_populates="sessions")

    def __repr__(self):
        return f"<Session {self.id} bot={self.bot_id} chat={self.external_id}>"
