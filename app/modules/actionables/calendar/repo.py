from app.core.db.repository import Repository
from app.core.logger import get_logger
from app.modules.actionables.calendar.db import (
    CalendarEvent,
    EmailReminder,
    EventAttendee,
    FollowUp,
)

logger = get_logger(__name__)


class CalendarRepository:
    def __init__(self):
        logger.debug("Initializing CalendarRepository.")
        self.event = Repository(CalendarEvent)
        self.reminder = Repository(EmailReminder)
        self.follow_up = Repository(FollowUp)
        self.attendee = Repository(EventAttendee)

    async def commit(self):
        await self.db_session.commit()
