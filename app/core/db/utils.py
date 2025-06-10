import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger

from .database import AsyncSessionLocal, async_engine

logger = get_logger(__name__)


async def execute_query(
    query: str, parameters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Execute a raw SQL query and return results"""
    logger.debug(f"Executing SQL query: {query[:100]}...")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text(query), parameters or {})
            rows = [dict(row._mapping) for row in result.fetchall()]
            logger.info(f"Query executed successfully, returned {len(rows)} rows.")
            return rows
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise


async def execute_query_single(
    query: str, parameters: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Execute a raw SQL query and return a single result"""
    results = await execute_query(query, parameters)
    return results[0] if results else None


async def check_database_connection() -> bool:
    """Check if database connection is working"""
    logger.debug("Checking database connection.")
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection is healthy.")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def get_database_info() -> Dict[str, Any]:
    """Get database connection and version information"""
    logger.debug("Retrieving database information.")
    try:
        info = await execute_query_single("SELECT version() as version")
        connection_info = {
            "status": "connected",
            "version": info.get("version") if info else "unknown",
            "pool_size": async_engine.pool.size(),
            "checked_in": async_engine.pool.checkedin(),
            "checked_out": async_engine.pool.checkedout(),
        }
        logger.info("Database information retrieved successfully.")
        return connection_info
    except Exception as e:
        logger.error(f"Error retrieving database information: {e}")
        return {"status": "error", "error": str(e)}


class DatabaseTransaction:
    """Context manager for database transactions"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        logger.debug("Starting database transaction.")
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Transaction failed, rolling back: {exc_val}")
            await self.session.rollback()
        else:
            logger.debug("Transaction completed successfully, committing.")
            await self.session.commit()


async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for transaction management"""
    async with AsyncSessionLocal() as session:
        async with DatabaseTransaction(session) as tx_session:
            yield tx_session


if __name__ == "__main__":

    async def main():
        print("Testing database connection...")
        if await check_database_connection():
            print("Database connection successful!")
            info = await get_database_info()
            print(f"Database info: {info}")
        else:
            print("Database connection failed!")

    asyncio.run(main())
