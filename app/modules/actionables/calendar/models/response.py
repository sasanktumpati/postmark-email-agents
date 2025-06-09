from typing import List, Literal, Union

from pydantic import BaseModel, Field

from app.modules.actionables.calendar.models.request import (
    AddReminderModel,
    CreateEventModel,
    CreateFollowUpModel,
)


class EventCreation(BaseModel):
    type: Literal["event"] = "event"
    data: CreateEventModel


class ReminderCreation(BaseModel):
    type: Literal["reminder"] = "reminder"
    data: AddReminderModel


class FollowUpCreation(BaseModel):
    type: Literal["follow_up"] = "follow_up"
    data: CreateFollowUpModel


class CalendarAction(BaseModel):
    """The action to be taken by the calendar agent."""

    action: Union[EventCreation, ReminderCreation, FollowUpCreation] = Field(
        ..., discriminator="type"
    )


class CalendarAgentResponse(BaseModel):
    """The response from the calendar agent, containing a list of actions."""

    actions: List[CalendarAction]
