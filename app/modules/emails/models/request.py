from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailSender(BaseModel):
    """Model for email sender information."""

    Email: EmailStr
    Name: Optional[str] = None
    MailboxHash: Optional[str] = ""


class EmailRecipientInfo(BaseModel):
    """Model for email recipient information (To, CC, BCC)."""

    Email: EmailStr
    Name: Optional[str] = None
    MailboxHash: Optional[str] = ""


class EmailAttachmentData(BaseModel):
    """Model for email attachment data from webhook."""

    Name: str
    Content: str  # Base64 encoded content
    ContentType: str
    ContentLength: int
    ContentID: Optional[str] = None


class EmailHeaderData(BaseModel):
    """Model for email header data from webhook."""

    Name: str
    Value: str


class PostmarkWebhookRequest(BaseModel):
    """Model for Postmark inbound email webhook request."""

    From: EmailStr
    MessageStream: Optional[str] = "inbound"
    FromName: Optional[str] = None
    FromFull: EmailSender
    To: Optional[str] = None
    ToFull: Optional[List[EmailRecipientInfo]] = Field(default_factory=list)
    Cc: Optional[str] = ""
    CcFull: Optional[List[EmailRecipientInfo]] = Field(default_factory=list)
    Bcc: Optional[str] = ""
    BccFull: Optional[List[EmailRecipientInfo]] = Field(default_factory=list)
    OriginalRecipient: Optional[str] = None
    ReplyTo: Optional[str] = ""
    Subject: Optional[str] = ""
    MessageID: str
    Date: str
    MailboxHash: Optional[str] = ""
    TextBody: Optional[str] = None
    HtmlBody: Optional[str] = None
    StrippedTextReply: Optional[str] = None
    Tag: Optional[str] = ""
    Headers: List[EmailHeaderData] = Field(default_factory=list)
    Attachments: Optional[List[EmailAttachmentData]] = Field(default_factory=list)


class EmailSearchRequest(BaseModel):
    """Request model for searching emails."""

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
    date_from: Optional[str] = Field(
        None, description="Filter emails from this date (ISO format)"
    )
    date_to: Optional[str] = Field(
        None, description="Filter emails until this date (ISO format)"
    )
    spam_status: Optional[str] = Field(
        None, description="Filter by spam status (yes, no, unknown)"
    )
    message_stream: Optional[str] = Field(None, description="Filter by message stream")

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


class EmailListRequest(BaseModel):
    """Request model for listing emails with pagination."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")
    search: Optional[EmailSearchRequest] = Field(None, description="Search parameters")
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


class EmailThreadRequest(BaseModel):
    """Request model for creating or updating email threads."""

    thread_id: Optional[str] = Field(None, description="Unique thread identifier")
    subject: Optional[str] = Field(None, description="Thread subject")
    thread_summary: Optional[str] = Field(None, description="Summary of the thread")


class EmailThreadSearchRequest(BaseModel):
    """Request model for searching email threads."""

    query: Optional[str] = Field(
        None, description="Search in thread subject and summary"
    )
    subject: Optional[str] = Field(
        None, description="Filter by thread subject (partial match)"
    )
    thread_summary: Optional[str] = Field(
        None, description="Filter by thread summary (partial match)"
    )
    min_email_count: Optional[int] = Field(
        None, ge=1, description="Minimum number of emails in thread"
    )
    max_email_count: Optional[int] = Field(
        None, ge=1, description="Maximum number of emails in thread"
    )
    date_from: Optional[str] = Field(
        None, description="Filter threads created from this date (ISO format)"
    )
    date_to: Optional[str] = Field(
        None, description="Filter threads created until this date (ISO format)"
    )
    updated_from: Optional[str] = Field(
        None, description="Filter threads updated from this date (ISO format)"
    )
    updated_to: Optional[str] = Field(
        None, description="Filter threads updated until this date (ISO format)"
    )


class EmailThreadListRequest(BaseModel):
    """Request model for listing email threads with pagination."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")
    search: Optional[EmailThreadSearchRequest] = Field(
        None, description="Thread search parameters"
    )
    sort_by: str = Field("updated_at", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed_fields = [
            "created_at",
            "updated_at",
            "subject",
            "email_count",
            "thread_id",
        ]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {', '.join(allowed_fields)}")
        return v
