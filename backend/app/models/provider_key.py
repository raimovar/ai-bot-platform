"""
Provider API Key model - stores encrypted API keys per provider per user.
"""
import uuid
import base64
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def encrypt_key(api_key: str, key_id: str) -> str:
    """Simple encoding (in production use proper encryption)."""
    combined = f"{key_id}:{api_key}"
    return base64.b64encode(combined.encode()).decode()


def decrypt_key(encrypted: str) -> str:
    """Simple decoding."""
    try:
        decoded = base64.b64decode(encrypted.encode()).decode()
        # Skip the key_id prefix
        return decoded.split(":", 1)[1]
    except Exception:
        return ""


class ProviderKey(Base):
    """User's API key for a specific provider."""
    
    __tablename__ = "provider_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Provider identifier (openai, anthropic, etc.)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Encrypted API key
    encrypted_key: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Optional custom base URL for this provider
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # User-friendly label
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Is this the default key for this provider?
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Active or disabled
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    def get_api_key(self) -> str:
        """Decrypt and return the API key."""
        return decrypt_key(self.encrypted_key)
    
    def __repr__(self) -> str:
        return f"<ProviderKey {self.provider}>"