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


class EmailListItemResponse(BaseModel):
    """Response model for email list items."""

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


class EmailStatsResponse(BaseModel):
    """Response model for email statistics."""

    total_emails: int
    non_spam_emails: int
    spam_emails: int
    unique_senders: int
    last_updated: Optional[datetime] = Field(default_factory=datetime.now)


class WebhookProcessingResponse(BaseModel):
    """Response model for webhook processing result."""

    email_id: str = Field(..., description="Database ID of the processed email")
    raw_email_id: str = Field(..., description="ID of the raw email data stored")
    message_id: str = Field(..., description="Postmark MessageID")
    processing_status: str = Field(..., description="Processing status")
    is_duplicate: bool = Field(
        default=False, description="Whether this was a duplicate email"
    )
    processing_time_ms: Optional[float] = Field(
        None, description="Time taken to process in milliseconds"
    )
    attachments_count: Optional[int] = Field(
        None, description="Number of attachments processed"
    )
