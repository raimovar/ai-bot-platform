"""
Knowledge Base models - documents and embeddings.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class KnowledgeSource(Base):
    """Knowledge source - uploaded document or URL."""
    
    __tablename__ = "knowledge_sources"
    
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
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Source type
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # file, url, text, api
    
    # File info
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # URL
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending"
    )  # pending, downloading, parsing, indexing, ready, error
    
    # Progress
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    indexed_chunks: Mapped[int] = mapped_column(Integer, default=0)
    
    # Configuration
    chunk_size: Mapped[int] = mapped_column(Integer, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50)
    
    # Error info
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Access control
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    bot = relationship("Bot", back_populates="knowledge_sources")
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="source",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeSource {self.name}>"


class KnowledgeChunk(Base):
    """Knowledge chunk - indexed piece of content."""
    
    __tablename__ = "knowledge_chunks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Position in source
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Embedding vector (for pgvector)
    embedding: Mapped[list[float] | None] = mapped_column(
        JSON,
        nullable=True
    )  # Store as JSON array for compatibility
    
    # Vector ID (for external vector DB like Qdrant)
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Stats
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationships
    source = relationship("KnowledgeSource", back_populates="chunks")
    
    def __repr__(self) -> str:
        return f"<KnowledgeChunk {self.chunk_index}>"
