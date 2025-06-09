from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.repository import TransactionalRepository
from app.modules.actionables.calendar.db import (
    CalendarEvent,
    EmailReminder,
    EventAttendee,
    FollowUp,
)


class CalendarRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.event = TransactionalRepository(db_session, CalendarEvent)
        self.reminder = TransactionalRepository(db_session, EmailReminder)
        self.follow_up = TransactionalRepository(db_session, FollowUp)
        self.attendee = TransactionalRepository(db_session, EventAttendee)

    async def commit(self):
        await self.db_session.commit()
