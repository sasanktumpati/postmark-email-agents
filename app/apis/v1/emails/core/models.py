import base64
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailRecipientResponse(BaseModel):
    """Response model for email recipients."""

    id: int
    recipient_type: str
    email_address: EmailStr
    name: Optional[str] = None
    mailbox_hash: Optional[str] = None


class EmailAttachmentResponse(BaseModel):
    """Response model for email attachments."""

    id: int
    filename: str
    content_type: str
    content_length: int
    content_id: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime


class EmailHeaderResponse(BaseModel):
    """Response model for email headers."""

    id: int
    name: str
    value: Optional[str] = None


class EmailListResponse(BaseModel):
    """Response model for email list."""

    id: int
    message_id: str
    message_stream: Optional[str] = None
    from_email: EmailStr
    from_name: Optional[str] = None
    subject: Optional[str] = None
    sent_at: Optional[datetime] = None
    processed_at: datetime
    mailbox_hash: Optional[str] = None
    tag: Optional[str] = None
    original_recipient: Optional[str] = None
    reply_to: Optional[str] = None
    spam_score: Optional[float] = None
    spam_status: str
    stripped_text_body: Optional[str] = None
    has_attachments: bool = False
    attachment_count: int = 0
    recipient_count: int = 0

    @field_validator("stripped_text_body", mode="before")
    @classmethod
    def decode_stripped_text_body(cls, v):
        if v and isinstance(v, str):
            try:
                return base64.b64decode(v).decode("utf-8")
            except Exception:
                return v
        return v


class EmailDetailResponse(BaseModel):
    """Response model for detailed email information."""

    id: int
    raw_email_id: int
    message_id: str
    message_stream: Optional[str] = None
    from_email: EmailStr
    from_name: Optional[str] = None
    subject: Optional[str] = None
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    stripped_text_body: Optional[str] = None
    sent_at: Optional[datetime] = None
    processed_at: datetime
    mailbox_hash: Optional[str] = None
    tag: Optional[str] = None
    original_recipient: Optional[str] = None
    reply_to: Optional[str] = None
    parent_email_id: Optional[int] = None
    parent_email_identifier: Optional[str] = None
    email_identifier: str
    spam_score: Optional[float] = None
    spam_status: str
    recipients: List[EmailRecipientResponse] = Field(default_factory=list)
    attachments: List[EmailAttachmentResponse] = Field(default_factory=list)
    headers: List[EmailHeaderResponse] = Field(default_factory=list)

    @field_validator("text_body", "html_body", "stripped_text_body", mode="before")
    @classmethod
    def decode_body_fields(cls, v):
        if v and isinstance(v, str):
            try:
                return base64.b64decode(v).decode("utf-8")
            except Exception:
                return v
        return v


class EmailThreadResponse(BaseModel):
    """Response model for email thread."""

    thread_id: str
    emails: List[EmailDetailResponse]
    total_emails: int
    thread_depth: int


class EmailSearchParams(BaseModel):
    """Search parameters for email queries."""

    query: Optional[str] = Field(
        None, description="Search in subject, body, and sender"
    )
    from_email: Optional[str] = Field(None, description="Filter by sender email")
    to_email: Optional[str] = Field(None, description="Filter by recipient email")
    subject: Optional[str] = Field(
        None, description="Filter by subject (partial match)"
    )
    mailbox_hash: Optional[str] = Field(None, description="Filter by mailbox hash")
    tag: Optional[str] = Field(None, description="Filter by tag")
    has_attachments: Optional[bool] = Field(
        None, description="Filter emails with/without attachments"
    )
    date_from: Optional[datetime] = Field(
        None, description="Filter emails from this date"
    )
    date_to: Optional[datetime] = Field(
        None, description="Filter emails until this date"
    )
    spam_status: Optional[str] = Field(
        None, description="Filter by spam status (yes, no, unknown)"
    )

    @field_validator("spam_status")
    @classmethod
    def validate_spam_status(cls, v):
        if v is not None:
            allowed_values = ["yes", "no", "unknown"]
            if v.lower() not in allowed_values:
                raise ValueError(
                    f"spam_status must be one of: {', '.join(allowed_values)}"
                )
            return v.lower()
        return v

    message_stream: Optional[str] = Field(None, description="Filter by message stream")


class EmailListRequest(BaseModel):
    """Request model for listing emails with pagination."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")
    search: Optional[EmailSearchParams] = Field(None, description="Search parameters")
    sort_by: str = Field("sent_at", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed_fields = [
            "sent_at",
            "processed_at",
            "from_email",
            "subject",
            "spam_score",
            "message_id",
        ]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {', '.join(allowed_fields)}")
        return v
