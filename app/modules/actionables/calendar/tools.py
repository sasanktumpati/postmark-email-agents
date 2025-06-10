from dataclasses import dataclass
import logging

from pydantic_ai import RunContext

from app.core.db.database import get_db_transaction
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

logger = logging.getLogger(__name__)


@dataclass
class CalendarDependencies:
    email_id: int


async def create_event(
    ctx: RunContext[CalendarDependencies], event_data: CreateEventModel
) -> str:
    """Create a calendar event based on the email content."""
    logger.info(
        f"TOOL CALLED: create_event for email_id {ctx.deps.email_id} with data: {event_data}"
    )

    try:
        repo = CalendarRepository()
        async with get_db_transaction() as session:
            event = await repo.event.create(
                session,
                CalendarEvent(
                    email_id=ctx.deps.email_id,
                    title=event_data.title,
                    description=event_data.description,
                    start_time=event_data.start_time,
                    end_time=event_data.end_time,
                    location=event_data.location,
                    priority=event_data.priority,
                ),
            )
            logger.info(f"Created calendar event with ID: {event.id}")

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
                await repo.attendee.create_many(session, attendees)
                logger.info(f"Created {len(attendees)} attendees for event {event.id}")

            if event_data.organizer:
                await repo.attendee.create(
                    session,
                    EventAttendee(
                        event_id=event.id,
                        email=event_data.organizer.email,
                        name=event_data.organizer.name,
                        is_organizer=True,
                    ),
                )
                logger.info(f"Created organizer for event {event.id}")

            result = f"Event '{event_data.title}' created successfully with {event_data.priority.value} priority."
            logger.info(f"TOOL SUCCESS: create_event - {result}")
            return result
    except Exception as e:
        logger.error(
            f"TOOL ERROR: create_event failed for email_id {ctx.deps.email_id}: {str(e)}",
            exc_info=True,
        )
        raise


async def add_reminder(
    ctx: RunContext[CalendarDependencies], reminder_data: AddReminderModel
) -> str:
    """Add a reminder to the user's calendar based on the email content."""
    logger.info(
        f"TOOL CALLED: add_reminder for email_id {ctx.deps.email_id} with data: {reminder_data}"
    )

    try:
        repo = CalendarRepository()
        async with get_db_transaction() as session:
            reminder = await repo.reminder.create(
                session,
                EmailReminder(
                    email_id=ctx.deps.email_id,
                    reminder_time=reminder_data.reminder_time,
                    note=reminder_data.note,
                    priority=reminder_data.priority,
                ),
            )
            logger.info(f"Created reminder with ID: {reminder.id}")

            result = f"Reminder added successfully with {reminder_data.priority.value} priority."
            logger.info(f"TOOL SUCCESS: add_reminder - {result}")
            return result
    except Exception as e:
        logger.error(
            f"TOOL ERROR: add_reminder failed for email_id {ctx.deps.email_id}: {str(e)}",
            exc_info=True,
        )
        raise


async def create_follow_up(
    ctx: RunContext[CalendarDependencies], follow_up_data: CreateFollowUpModel
) -> str:
    """Create a follow-up for an email."""
    logger.info(
        f"TOOL CALLED: create_follow_up for email_id {ctx.deps.email_id} with data: {follow_up_data}"
    )

    try:
        repo = CalendarRepository()
        async with get_db_transaction() as session:
            follow_up = await repo.follow_up.create(
                session,
                FollowUp(
                    email_id=ctx.deps.email_id,
                    follow_up_time=follow_up_data.follow_up_time,
                    note=follow_up_data.note,
                    priority=follow_up_data.priority,
                ),
            )
            logger.info(f"Created follow-up with ID: {follow_up.id}")

            result = f"Follow-up scheduled for {follow_up_data.follow_up_time} with {follow_up_data.priority.value} priority."
            logger.info(f"TOOL SUCCESS: create_follow_up - {result}")
            return result
    except Exception as e:
        logger.error(
            f"TOOL ERROR: create_follow_up failed for email_id {ctx.deps.email_id}: {str(e)}",
            exc_info=True,
        )
        raise
