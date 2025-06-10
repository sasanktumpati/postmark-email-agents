from datetime import datetime
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from app.modules.actionables.calendar.db import (
    EventStatus,
    FollowUpStatus,
    ReminderStatus,
)
from app.modules.actionables.shopping.db import Currency


class ActionableType(str, Enum):
    CALENDAR_EVENT = "calendar_event"
    REMINDER = "reminder"
    FOLLOW_UP = "follow_up"
    NOTE = "note"
    BILL = "bill"
    COUPON = "coupon"


class EventAttendeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: Optional[str] = None
    is_organizer: bool


class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    status: EventStatus
    attendees: List[EventAttendeeResponse] = []
    type: str = Field(default="calendar_event", description="Type of actionable")


class EmailReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    reminder_time: datetime
    note: Optional[str] = None
    status: ReminderStatus
    type: str = Field(default="reminder", description="Type of actionable")


class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    follow_up_time: datetime
    note: Optional[str] = None
    status: FollowUpStatus
    type: str = Field(default="follow_up", description="Type of actionable")


class EmailNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    note: str
    type: str = Field(default="note", description="Type of actionable")


class BillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    vendor: str
    amount: float
    currency: Currency
    due_date: Optional[datetime] = None
    payment_url: Optional[str] = None
    type: str = Field(default="bill", description="Type of actionable")


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    vendor: str
    code: str
    discount: Optional[str] = None
    expiry_date: Optional[datetime] = None
    type: str = Field(default="coupon", description="Type of actionable")


ActionableObject = Union[
    CalendarEventResponse,
    EmailReminderResponse,
    FollowUpResponse,
    EmailNoteResponse,
    BillResponse,
    CouponResponse,
]


class ActionableListRequest(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(10, ge=1, le=100, description="Number of items per page")
    email_id: Optional[int] = Field(None, description="Filter by a specific email ID")
    thread_id: Optional[str] = Field(
        None, description="Filter by a specific email thread ID"
    )
    actionable_types: Optional[List[ActionableType]] = Field(
        None, description="Filter by actionable types"
    )
    start_date: Optional[datetime] = Field(
        None, description="Filter actionables from this date"
    )
    end_date: Optional[datetime] = Field(
        None, description="Filter actionables up to this date"
    )


class CalendarActionables(BaseModel):
    events: List[CalendarEventResponse] = []
    reminders: List[EmailReminderResponse] = []
    follow_ups: List[FollowUpResponse] = []


class NotesActionables(BaseModel):
    notes: List[EmailNoteResponse] = []


class ShoppingActionables(BaseModel):
    bills: List[BillResponse] = []
    coupons: List[CouponResponse] = []


class GroupedActionablesResponse(BaseModel):
    calendar: CalendarActionables
    notes: NotesActionables
    shopping: ShoppingActionables
    total_count: int
