import enum

from sqlalchemy import (
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


class Priority(enum.Enum):
    """Enum for priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NoteCategory(enum.Enum):
    """Enum for note categories."""

    GENERAL = "general"
    MEETING = "meeting"
    TASK = "task"
    IDEA = "idea"
    DECISION = "decision"
    CONTACT = "contact"
    INFORMATION = "information"


class EmailNote(Base):
    """Model for notes created from emails."""

    __tablename__ = "email_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    note = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    category = Column(Enum(NoteCategory), default=NoteCategory.GENERAL)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = relationship("Email", backref="notes")
