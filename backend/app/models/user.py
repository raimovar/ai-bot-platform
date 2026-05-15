"""
User model with RBAC support.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.core.database import Base


class User(Base):
    """User model with role-based access control."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    role: Mapped[str] = mapped_column(
        String(50),
        default="user",
        nullable=False
    )  # admin, user, viewer
    
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Bot creation limits
    max_bots: Mapped[int] = mapped_column(default=10)
    
    # Telegram
    telegram_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    bots = relationship("Bot", back_populates="owner", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<User {self.username}>"
