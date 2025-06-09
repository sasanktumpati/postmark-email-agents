from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Attendee(BaseModel):
    email: str = Field(..., description="Email of the attendee.")
    name: Optional[str] = Field(None, description="Name of the attendee.")


class CreateEventModel(BaseModel):
    """Tool call model for creating a calendar event."""

    title: str = Field(..., description="Title of the event.")
    start_time: datetime = Field(..., description="Start time of the event.")
    end_time: datetime = Field(..., description="End time of the event.")
    description: Optional[str] = Field(None, description="Description of the event.")
    location: Optional[str] = Field(None, description="Location of the event.")
    attendees: Optional[List[Attendee]] = Field(
        None, description="List of attendees for the event."
    )
    organizer: Optional[Attendee] = Field(None, description="Organizer of the event.")


class AddReminderModel(BaseModel):
    """Tool call model for adding a reminder."""

    reminder_time: datetime = Field(..., description="Time for the reminder.")
    note: str = Field(..., description="Note for the reminder.")


class CreateFollowUpModel(BaseModel):
    """Tool call model for creating a follow-up."""

    follow_up_time: datetime = Field(..., description="Time for the follow-up.")
    note: str = Field(..., description="Note for the follow-up.")
