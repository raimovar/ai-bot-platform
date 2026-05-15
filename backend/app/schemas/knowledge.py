"""
Knowledge Base schemas for API validation.
"""
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────────────────────────────────────────
# Knowledge Source Schemas
# ─────────────────────────────────────────────────────────────

class KnowledgeSourceCreate(BaseModel):
    """Schema for creating a knowledge source."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Source type
    source_type: str = Field(..., description="file, url, text, api")
    
    # File upload (handled separately with multipart)
    file_name: Optional[str] = None
    
    # URL
    url: Optional[str] = Field(None, max_length=2000)
    
    # Text content
    content: Optional[str] = None
    
    # Configuration
    chunk_size: int = Field(500, ge=100, le=2000)
    chunk_overlap: int = Field(50, ge=0, le=500)


class KnowledgeSourceUpdate(BaseModel):
    """Schema for updating a knowledge source."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    chunk_size: Optional[int] = Field(None, ge=100, le=2000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500)


class KnowledgeSourceResponse(BaseModel):
    """Schema for knowledge source response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    bot_id: uuid.UUID
    name: str
    description: Optional[str] = None
    source_type: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    url: Optional[str] = None
    status: str
    total_chunks: int
    indexed_chunks: int
    error_message: Optional[str] = None
    metadata: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None


class KnowledgeSourceListResponse(BaseModel):
    """Schema for paginated knowledge source list."""
    items: list[KnowledgeSourceResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ─────────────────────────────────────────────────────────────
# Knowledge Chunk Schemas
# ─────────────────────────────────────────────────────────────

class KnowledgeChunkResponse(BaseModel):
    """Schema for knowledge chunk response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    source_id: uuid.UUID
    content: str
    chunk_index: int
    token_count: Optional[int] = None
    metadata: dict
    created_at: datetime


class KnowledgeSearchRequest(BaseModel):
    """Schema for searching knowledge base."""
    query: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=20)
    source_ids: Optional[list[uuid.UUID]] = None


class KnowledgeSearchResponse(BaseModel):
    """Schema for knowledge search results."""
    chunks: list[KnowledgeChunkResponse]
    sources: dict[str, str]  # source_id -> source_name
    total: int
    query: str


# ─────────────────────────────────────────────────────────────
# Document Upload
# ─────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    source_id: uuid.UUID
    file_name: str
    file_size: int
    status: str
    message: str
