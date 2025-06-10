from app.core.logger import get_logger

from .database import Base, get_async_db, init_db

logger = get_logger(__name__)
logger.info("Initializing database module.")

__all__ = [
    "Base",
    "get_async_db",
    "init_db_async",
]


async def init_db_async():
    """Initialize the database by creating all tables (async version)."""
    logger.info("Starting database initialization.")
    from app.modules.actionables.calendar.db import (  # noqa: F401
        CalendarEvent,
        EmailReminder,
        EventAttendee,
        FollowUp,
    )
    from app.modules.actionables.notes.db import (  # noqa: F401
        EmailNote,
    )
    from app.modules.actionables.shopping.db import (  # noqa: F401
        Bill,
        Coupon,
    )
    from app.modules.emails.models import db  # noqa: F401

    await init_db()
    logger.info("Database initialization completed successfully.")
