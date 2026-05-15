"""
AI Bot Platform - Core Configuration
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # App
    APP_NAME: str = "AI Bot Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aibotdb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI Services
    AI_GATEWAY_URL: str = "http://ai-gateway:8002"
    BOT_RUNTIME_URL: str = "http://bot-runtime:8001"
    
    # Telegram
    TELEGRAM_WEBHOOK_SECRET: str = ""
    
    # Storage
    STORAGE_URL: str = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET: str = "aibot-knowledge"
    
    # CORS - comma-separated string, converted to list
    CORS_ORIGINS_RAW: str = "*"
    
    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Convert comma-separated string to list."""
        if self.CORS_ORIGINS_RAW == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
