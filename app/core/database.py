"""
Database connection and session management for the Fleek Media Service.
Handles async database operations using SQLAlchemy and SQLModel.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.api_debug,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    """
    Dependency to get database session.
    Used with FastAPI dependency injection.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
