"""Application configuration settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/executive_ai"
    redis_url: str = "redis://redis:6379"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8000"
    ]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()