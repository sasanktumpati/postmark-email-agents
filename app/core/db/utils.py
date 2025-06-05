import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal, async_engine


async def execute_query(
    query: str, parameters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Execute a raw SQL query and return results"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(query), parameters or {})
        return [dict(row._mapping) for row in result.fetchall()]


async def execute_query_single(
    query: str, parameters: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Execute a raw SQL query and return a single result"""
    results = await execute_query(query, parameters)
    return results[0] if results else None


async def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def get_database_info() -> Dict[str, Any]:
    """Get database connection and version information"""
    try:
        info = await execute_query_single("SELECT version() as version")
        connection_info = {
            "status": "connected",
            "version": info.get("version") if info else "unknown",
            "pool_size": async_engine.pool.size(),
            "checked_in": async_engine.pool.checkedin(),
            "checked_out": async_engine.pool.checkedout(),
        }
        return connection_info
    except Exception as e:
        return {"status": "error", "error": str(e)}


class DatabaseTransaction:
    """Context manager for database transactions"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.session.rollback()
        else:
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
