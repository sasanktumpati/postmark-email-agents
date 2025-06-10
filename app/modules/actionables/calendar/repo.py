from app.core.db.repository import Repository
from app.modules.actionables.calendar.db import (
    CalendarEvent,
    EmailReminder,
    EventAttendee,
    FollowUp,
)


class CalendarRepository:
    def __init__(self):
        self.event = Repository(CalendarEvent)
        self.reminder = Repository(EmailReminder)
        self.follow_up = Repository(FollowUp)
        self.attendee = Repository(EventAttendee)

    async def commit(self):
        await self.db_session.commit()
