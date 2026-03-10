"""Database connection and session management."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_async_session_factory = None


def get_async_database_url() -> str:
    """Convert sync database URL to async URL."""
    settings = get_settings()
    url = settings.database_url
    
    # Convert postgresql:// to postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    return url


async def init_database() -> None:
    """Initialize the database engine and session factory."""
    global _engine, _async_session_factory
    
    if _engine is not None:
        return
    
    database_url = get_async_database_url()
    
    _engine = create_async_engine(
        database_url,
        poolclass=NullPool,  # Use NullPool for async
        echo=get_settings().debug,
    )
    
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    logger.info("Database engine initialized")


async def close_database() -> None:
    """Close the database engine."""
    global _engine, _async_session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database engine closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    global _async_session_factory
    
    if _async_session_factory is None:
        await init_database()
    
    async with _async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def execute_migration(sql: str) -> None:
    """Execute a raw SQL migration."""
    async with get_db_session() as session:
        from sqlalchemy import text
        await session.execute(text(sql))
        await session.commit()
