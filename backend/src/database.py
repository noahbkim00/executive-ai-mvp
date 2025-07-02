"""Database configuration and connection management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .config import get_settings
from .models.base import Base


settings = get_settings()

# Create async engine (only if not running alembic)
engine = None
AsyncSessionLocal = None

def init_database():
    """Initialize database engine and session factory"""
    global engine, AsyncSessionLocal
    if engine is None:
        # Ensure we're using asyncpg
        db_url = settings.database_url
        if not db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            
        engine = create_async_engine(
            db_url,
            echo=False,
        )
        
        # Create session factory
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

# Initialize if not running under alembic
import os
if not os.environ.get('ALEMBIC_CONFIG'):
    init_database()


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    if AsyncSessionLocal is None:
        init_database()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()