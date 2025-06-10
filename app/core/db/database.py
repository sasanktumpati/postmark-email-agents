from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logger import get_logger

load_dotenv()

logger = get_logger(__name__)
logger.info("Initializing database engine and session factory.")


async_engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    echo=settings.sql_echo,
    future=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

logger.info("Database engine and session factory initialized successfully.")


class Base(DeclarativeBase):
    pass


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency with proper transaction management"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database session error, rolling back: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for independent operations"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error, rolling back: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session with automatic transaction management"""
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("Yielding database session with transaction")
            yield session
            await session.commit()
            logger.debug("Database transaction committed")
        except Exception as e:
            logger.error(
                f"Database transaction failed, rolling back: {e}", exc_info=True
            )
            await session.rollback()
            raise
        finally:
            logger.debug("Closing database session")
            await session.close()


async def init_db() -> None:
    """Initialize database tables and reset sequences"""
    logger.info("Creating database tables.")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")


async def close_db() -> None:
    """Close database connections"""
    logger.info("Closing database connections.")
    await async_engine.dispose()
    logger.info("Database connections closed.")
