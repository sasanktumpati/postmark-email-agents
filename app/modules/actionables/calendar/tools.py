from dataclasses import dataclass

from pydantic_ai import RunContext

from app.core.db.database import get_db_session
from app.modules.actionables.calendar.db import (
    CalendarEvent,
    EmailReminder,
    EventAttendee,
    FollowUp,
)
from app.modules.actionables.calendar.models.request import (
    AddReminderModel,
    CreateEventModel,
    CreateFollowUpModel,
)
from app.modules.actionables.calendar.repo import CalendarRepository


@dataclass
class CalendarDependencies:
    email_id: int


async def create_event(
    ctx: RunContext[CalendarDependencies], event_data: CreateEventModel
) -> str:
    """Create a calendar event based on the email content."""
    async with get_db_session() as session:
        repo = CalendarRepository(session)
        event = await repo.event.create(
            CalendarEvent(
                email_id=ctx.deps.email_id,
                title=event_data.title,
                description=event_data.description,
                start_time=event_data.start_time,
                end_time=event_data.end_time,
                location=event_data.location,
            ),
            commit=False,
        )
        await repo.event.flush()

        if event_data.attendees:
            attendees = []
            for attendee_data in event_data.attendees:
                attendees.append(
                    EventAttendee(
                        event_id=event.id,
                        email=attendee_data.email,
                        name=attendee_data.name,
                        is_organizer=False,
                    )
                )
            await repo.attendee.create_many(attendees, commit=False)

        if event_data.organizer:
            await repo.attendee.create(
                EventAttendee(
                    event_id=event.id,
                    email=event_data.organizer.email,
                    name=event_data.organizer.name,
                    is_organizer=True,
                ),
                commit=False,
            )

        await repo.commit()
        return f"Event '{event_data.title}' created successfully."


async def add_reminder(
    ctx: RunContext[CalendarDependencies], reminder_data: AddReminderModel
) -> str:
    """Add a reminder for an email."""
    async with get_db_session() as session:
        repo = CalendarRepository(session)
        await repo.reminder.create(
            EmailReminder(
                email_id=ctx.deps.email_id,
                reminder_time=reminder_data.reminder_time,
                note=reminder_data.note,
            )
        )
        await repo.commit()
        return f"Reminder set for {reminder_data.reminder_time} with note '{reminder_data.note}'."


async def create_follow_up(
    ctx: RunContext[CalendarDependencies], follow_up_data: CreateFollowUpModel
) -> str:
    """Create a follow-up for an email."""
    async with get_db_session() as session:
        repo = CalendarRepository(session)
        await repo.follow_up.create(
            FollowUp(
                email_id=ctx.deps.email_id,
                follow_up_time=follow_up_data.follow_up_time,
                note=follow_up_data.note,
            )
        )
        await repo.commit()
        return f"Follow-up scheduled for {follow_up_data.follow_up_time} with note '{follow_up_data.note}'."
