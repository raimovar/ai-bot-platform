"""
Provider Keys management endpoints.
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.provider_key import ProviderKey

router = APIRouter()


def encrypt_key(api_key: str, key_id: str) -> str:
    """Simple encoding (in production use proper encryption)."""
    import base64
    combined = f"{key_id}:{api_key}"
    return base64.b64encode(combined.encode()).decode()


def serialize_key(key: ProviderKey) -> dict:
    """Serialize a provider key for API response."""
    return {
        "id": str(key.id),
        "provider": key.provider,
        "api_key": key.get_api_key(),
        "base_url": key.base_url,
        "label": key.label,
        "is_default": key.is_default,
        "is_active": key.is_active,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
    }


@router.get("/")
async def list_provider_keys(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all provider keys for current user."""
    query = select(ProviderKey).where(
        ProviderKey.user_id == uuid.UUID(current_user["id"]),
        ProviderKey.is_active == True
    )
    result = await db.execute(query)
    keys = result.scalars().all()
    
    return {
        "items": [serialize_key(key) for key in keys],
        "total": len(keys)
    }


@router.post("/")
async def create_provider_key(
    data: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Add a new provider API key."""
    user_id = uuid.UUID(current_user["id"])
    provider = data.get("provider", "")
    api_key = data.get("api_key", "")
    base_url = data.get("base_url")
    label = data.get("label")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    # Check if key for this provider already exists
    existing = await db.execute(
        select(ProviderKey).where(
            ProviderKey.user_id == user_id,
            ProviderKey.provider == provider,
            ProviderKey.is_active == True
        )
    )
    existing_key = existing.scalar_one_or_none()
    
    if existing_key:
        # Update existing key
        existing_key.encrypted_key = encrypt_key(api_key, str(existing_key.id))
        existing_key.base_url = base_url
        existing_key.label = label
        await db.commit()
        await db.refresh(existing_key)
        key = existing_key
    else:
        # Create new key
        key_id = uuid.uuid4()
        key = ProviderKey(
            id=key_id,
            user_id=user_id,
            provider=provider,
            encrypted_key=encrypt_key(api_key, str(key_id)),
            base_url=base_url,
            label=label,
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
    
    return serialize_key(key)


@router.get("/{key_id}")
async def get_provider_key(
    key_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a specific provider key."""
    query = select(ProviderKey).where(
        ProviderKey.id == key_id,
        ProviderKey.user_id == uuid.UUID(current_user["id"])
    )
    result = await db.execute(query)
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    
    return serialize_key(key)


@router.delete("/{key_id}")
async def delete_provider_key(
    key_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a provider key (soft delete)."""
    query = select(ProviderKey).where(
        ProviderKey.id == key_id,
        ProviderKey.user_id == uuid.UUID(current_user["id"])
    )
    result = await db.execute(query)
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    
    key.is_active = False
    await db.commit()
    
    return {"message": "Key deleted"}


@router.get("/by-provider/{provider}")
async def get_provider_key_by_provider(
    provider: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get user's API key for a specific provider."""
    query = select(ProviderKey).where(
        ProviderKey.user_id == uuid.UUID(current_user["id"]),
        ProviderKey.provider == provider,
        ProviderKey.is_active == True
    )
    result = await db.execute(query)
    key = result.scalar_one_or_none()
    
    if not key:
        return {"found": False, "provider": provider}
    
    return {
        "found": True,
        "provider": key.provider,
        "api_key": key.get_api_key(),
        "base_url": key.base_url,
    }