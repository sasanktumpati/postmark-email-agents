from .database import Base, get_async_db, init_db

__all__ = [
    "Base",
    "get_async_db",
    "init_db_async",
]


async def init_db_async():
    """Initialize the database by creating all tables (async version)."""
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
