"""Actionables models module."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EmailMessageData(BaseModel):
    """Structured email message data for agent processing."""

    message_id: str = Field(..., description="Unique message identifier")
    subject: Optional[str] = Field(None, description="Email subject")
    body: str = Field(..., description="Email body content")
    html_body: Optional[str] = Field(None, description="HTML body content")
    sender_name: Optional[str] = Field(None, description="Sender name")
    sender_email: str = Field(..., description="Sender email address")
    to_emails: List[str] = Field(default_factory=list, description="To recipients")
    cc_emails: List[str] = Field(default_factory=list, description="CC recipients")
    bcc_emails: List[str] = Field(default_factory=list, description="BCC recipients")
    sent_at: Optional[datetime] = Field(None, description="When email was sent")
    attachments: List[str] = Field(
        default_factory=list, description="Attachment filenames"
    )


class EmailThreadData(BaseModel):
    """Structured email thread data for agent processing."""

    thread_id: str = Field(..., description="Unique thread identifier")
    subject: Optional[str] = Field(None, description="Thread subject")
    messages: List[EmailMessageData] = Field(..., description="Messages in the thread")
    message_count: int = Field(..., description="Total number of messages in thread")
    created_at: Optional[datetime] = Field(None, description="Thread creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class ActionableType(str, Enum):
    """Types of actionables that can be created."""

    CALENDAR_EVENT = "calendar_event"
    REMINDER = "reminder"
    FOLLOW_UP = "follow_up"
    NOTE = "note"
    TASK = "task"
    BILL = "bill"
    COUPON = "coupon"


class ActionableRequest(BaseModel):
    """Base request model for actionable processing."""

    email_id: int = Field(..., description="ID of the email to process")
    thread_data: Optional[EmailThreadData] = Field(
        None, description="Thread context if available"
    )
    existing_actionables: List[Dict[str, Any]] = Field(
        default_factory=list, description="Existing actionables for this thread"
    )


class ActionableResponse(BaseModel):
    """Base response model for actionable processing."""

    actionable_type: ActionableType
    success: bool = Field(
        ..., description="Whether the actionable was created successfully"
    )
    actionable_id: Optional[int] = Field(None, description="ID of created actionable")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class BatchActionableResponse(BaseModel):
    """Response model for batch actionable processing."""

    email_id: int = Field(..., description="ID of the processed email")
    total_actionables: int = Field(
        ..., description="Total number of actionables created"
    )
    successful_actionables: List[ActionableResponse] = Field(default_factory=list)
    failed_actionables: List[ActionableResponse] = Field(default_factory=list)
    processing_time_ms: Optional[float] = Field(
        None, description="Processing time in milliseconds"
    )
