"""
Configuration for Bot Runtime.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aibotdb"
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_GATEWAY_URL: str = "http://localhost:8002"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
