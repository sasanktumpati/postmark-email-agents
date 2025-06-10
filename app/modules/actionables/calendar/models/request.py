from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.actionables.calendar.db import Priority


class Attendee(BaseModel):
    email: str = Field(..., description="Email of the attendee.")
    name: Optional[str] = Field(None, description="Name of the attendee.")


class CreateEventModel(BaseModel):
    """Tool call model for creating a calendar event."""

    title: str = Field(..., description="Clear, concise title of the event.")
    start_time: datetime = Field(
        ..., description="Start time of the event in ISO format."
    )
    end_time: datetime = Field(..., description="End time of the event in ISO format.")
    description: Optional[str] = Field(
        None,
        description="Detailed description of the event including agenda, purpose, or meeting details. Should be comprehensive but concise.",
    )
    location: Optional[str] = Field(
        None,
        description="Event location - can be physical address, room name, or virtual meeting link.",
    )
    attendees: Optional[List[Attendee]] = Field(
        None, description="List of attendees for the event."
    )
    organizer: Optional[Attendee] = Field(None, description="Organizer of the event.")
    priority: Priority = Field(
        Priority.MEDIUM,
        description="Priority level: urgent for critical deadlines, high for important meetings, medium for regular events, low for optional activities.",
    )


class AddReminderModel(BaseModel):
    """Tool call model for adding a reminder."""

    reminder_time: datetime = Field(
        ..., description="Time for the reminder in ISO format."
    )
    note: str = Field(
        ...,
        description="Detailed but concise reminder note including context, action needed, and relevant details. Should be clear and actionable.",
    )
    priority: Priority = Field(
        Priority.MEDIUM,
        description="Priority level: urgent for critical deadlines, high for important tasks, medium for regular reminders, low for nice-to-have items.",
    )


class CreateFollowUpModel(BaseModel):
    """Tool call model for creating a follow-up."""

    follow_up_time: datetime = Field(
        ..., description="Time for the follow-up in ISO format."
    )
    note: str = Field(
        ...,
        description="Detailed follow-up note including context, what needs to be followed up on, expected outcomes, and any relevant background information.",
    )
    priority: Priority = Field(
        Priority.MEDIUM,
        description="Priority level: urgent for critical follow-ups, high for important communications, medium for regular check-ins, low for optional follow-ups.",
    )
