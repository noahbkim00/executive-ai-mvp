"""Application configuration settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/executive_ai"
    redis_url: str = "redis://redis:6379"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8000"
    ]
    
    # AI API Keys
    openai_api_key: str = ""
    serper_api_key: str = ""
    
    # Optional LangChain Configuration
    langchain_tracing_v2: str = "false"
    langchain_api_key: str = ""
    
    # Research Configuration
    enable_web_search: bool = True
    research_timeout_seconds: int = 30
    
    # LangGraph Feature Flag
    use_langgraph: bool = True  # Phase 4 Complete - Full workflow with question generation
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()