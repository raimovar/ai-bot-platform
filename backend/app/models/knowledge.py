"""
Knowledge models for database
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base


class KnowledgeSource(Base):
    """Knowledge source (document) model"""

    __tablename__ = "knowledge_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # file, url, text

    # File info
    file_path = Column(String(500), nullable=True)
    url = Column(String(2000), nullable=True)

    # Processing status
    status = Column(String(50), default="pending")  # pending, indexing, ready, error
    error_message = Column(Text, nullable=True)

    # Statistics
    chunk_count = Column(Integer, default=0)
    total_chars = Column(Integer, default=0)

    # Extra data
    extra_data = Column(JSONB, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chunks = relationship("KnowledgeChunk", back_populates="source", cascade="all, delete-orphan")
    bot = relationship("Bot", back_populates="knowledge_sources")

    def __repr__(self):
        return f"<KnowledgeSource {self.id} name={self.name}>"


class KnowledgeChunk(Base):
    """Knowledge chunk with embedding"""

    __tablename__ = "knowledge_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False)

    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    # Embedding (stored as JSON array for pgvector compatibility)
    # In production, use pgvector extension directly
    embedding = Column(JSONB, default=list)

    # Extra data
    extra_data = Column(JSONB, default=dict)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source = relationship("KnowledgeSource", back_populates="chunks")

    # Indexes
    __table_args__ = (
        Index("ix_knowledge_chunks_source_id", "source_id"),
        Index("ix_knowledge_chunks_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<KnowledgeChunk {self.id} source={self.source_id}>"

    @property
    def preview(self) -> str:
        """Get content preview"""
        if len(self.content) > 100:
            return self.content[:100] + "..."
        return self.content
