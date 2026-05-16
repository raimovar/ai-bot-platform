"""
Provider Key schemas for API validation.
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProviderKeyCreate(BaseModel):
    """Schema for creating a provider key."""
    provider: str = Field(..., description="Provider identifier (openai, anthropic, etc.)")
    api_key: str = Field(..., min_length=1, description="The API key")
    base_url: Optional[str] = Field(None, description="Optional custom base URL")
    label: Optional[str] = Field(None, description="User-friendly label")


class ProviderKeyUpdate(BaseModel):
    """Schema for updating a provider key."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    label: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ProviderKeyResponse(BaseModel):
    """Schema for provider key response (masked API key)."""
    model_config = {"from_attributes": True}
    
    id: uuid.UUID
    provider: str
    base_url: Optional[str] = None
    label: Optional[str] = None
    is_default: bool
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    
    # Masked key for display (first 8 + last 4 chars)
    masked_key: str


class ProviderKeyListResponse(BaseModel):
    """Schema for paginated key list."""
    items: list
    total: int