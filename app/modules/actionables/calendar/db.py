import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class EventStatus(enum.Enum):
    """Enum for event statuses."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class ReminderStatus(enum.Enum):
    """Enum for reminder statuses."""

    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FollowUpStatus(enum.Enum):
    """Enum for follow-up statuses."""

    PENDING = "pending"
    COMPLETED = "completed"


class CalendarEvent(Base):
    """Model for calendar events extracted from emails."""

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255), nullable=True)
    status = Column(Enum(EventStatus), default=EventStatus.CONFIRMED)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = relationship("Email", backref="calendar_events")


class EmailReminder(Base):
    """Model for email reminders."""

    __tablename__ = "email_reminders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    reminder_time = Column(DateTime(timezone=True), nullable=False)
    note = Column(Text, nullable=True)
    status = Column(Enum(ReminderStatus), default=ReminderStatus.SCHEDULED)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = relationship("Email", backref="reminders")


class FollowUp(Base):
    """Model for email follow-ups."""

    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    follow_up_time = Column(DateTime(timezone=True), nullable=False)
    note = Column(Text, nullable=True)
    status = Column(Enum(FollowUpStatus), default=FollowUpStatus.PENDING)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = relationship("Email", backref="follow_ups")


class EventAttendee(Base):
    """Model for event attendees."""

    __tablename__ = "event_attendees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(
        Integer, ForeignKey("calendar_events.id"), nullable=False, index=True
    )
    email = Column(String(320), nullable=False)
    name = Column(String(255), nullable=True)
    is_organizer = Column(Boolean, default=False)

    event = relationship("CalendarEvent", backref="attendees")
