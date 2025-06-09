from datetime import datetime
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field

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
    id: int
    email: str
    name: Optional[str] = None
    is_organizer: bool

    class Config:
        from_attributes = True


class CalendarEventResponse(BaseModel):
    id: int
    email_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    status: EventStatus
    attendees: List[EventAttendeeResponse] = []

    class Config:
        from_attributes = True


class EmailReminderResponse(BaseModel):
    id: int
    email_id: int
    reminder_time: datetime
    note: Optional[str] = None
    status: ReminderStatus

    class Config:
        from_attributes = True


class FollowUpResponse(BaseModel):
    id: int
    email_id: int
    follow_up_time: datetime
    note: Optional[str] = None
    status: FollowUpStatus

    class Config:
        from_attributes = True


class EmailNoteResponse(BaseModel):
    id: int
    email_id: int
    note: str

    class Config:
        from_attributes = True


class BillResponse(BaseModel):
    id: int
    email_id: int
    vendor: str
    amount: float
    currency: Currency
    due_date: Optional[datetime] = None
    payment_url: Optional[str] = None

    class Config:
        from_attributes = True


class CouponResponse(BaseModel):
    id: int
    email_id: int
    vendor: str
    code: str
    discount: Optional[str] = None
    expiry_date: Optional[datetime] = None

    class Config:
        from_attributes = True


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
