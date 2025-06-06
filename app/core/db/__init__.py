from .database import Base, get_async_db, init_db

__all__ = [
    "Base",
    "get_async_db",
    "init_db_async",
]


async def init_db_async():
    """Initialize the database by creating all tables (async version)."""
    from app.modules.emails.models import db  # noqa: F401

    await init_db()
