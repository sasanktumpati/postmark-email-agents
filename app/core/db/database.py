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
from sqlalchemy.sql import text

from app.core.config import settings

load_dotenv()


async_engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    echo=settings.sql_echo,
    future=True,
    isolation_level="READ_COMMITTED",
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency with proper transaction management"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session with automatic transaction management"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def reset_sequences() -> None:
    """Reset database sequences to fix any sequence conflicts."""
    async with async_engine.begin() as conn:
        await conn.execute(
            text("""
            SELECT setval(pg_get_serial_sequence('calendar_events', 'id'), 
                         COALESCE((SELECT MAX(id) FROM calendar_events), 1));
            SELECT setval(pg_get_serial_sequence('email_reminders', 'id'), 
                         COALESCE((SELECT MAX(id) FROM email_reminders), 1));
            SELECT setval(pg_get_serial_sequence('follow_ups', 'id'), 
                         COALESCE((SELECT MAX(id) FROM follow_ups), 1));
            SELECT setval(pg_get_serial_sequence('email_notes', 'id'), 
                         COALESCE((SELECT MAX(id) FROM email_notes), 1));
            SELECT setval(pg_get_serial_sequence('bills', 'id'), 
                         COALESCE((SELECT MAX(id) FROM bills), 1));
            SELECT setval(pg_get_serial_sequence('coupons', 'id'), 
                         COALESCE((SELECT MAX(id) FROM coupons), 1));
            """)
        )


async def init_db() -> None:
    """Initialize database tables and reset sequences"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        await reset_sequences()
    except Exception:
        pass


async def close_db() -> None:
    """Close database connections"""
    await async_engine.dispose()
