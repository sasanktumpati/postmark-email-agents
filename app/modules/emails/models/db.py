import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class RecipientType(enum.Enum):
    """Enum for recipient types in emails."""

    FROM = "from"
    TO = "to"
    CC = "cc"
    BCC = "bcc"


class ProcessingStatus(enum.Enum):
    """Enum for processing status of raw emails."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class ActionablesProcessingStatus(enum.Enum):
    """Enum for actionables processing status of emails."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class SpamStatus(enum.Enum):
    """Enum for spam status of emails."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class EmailThread(Base):
    """Model for email threads to organize related emails."""

    __tablename__ = "email_threads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thread_id = Column(String(255), unique=True, index=True, nullable=False)
    subject = Column(String(998), nullable=True, index=True)
    thread_summary = Column(Text, nullable=True, comment="Summary of the email thread")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    email_count = Column(Integer, default=0, nullable=False)
    first_email_id = Column(
        Integer,
        ForeignKey("emails.id"),
        nullable=True,
        comment="Reference to the first email in thread",
    )
    last_email_id = Column(
        Integer,
        ForeignKey("emails.id"),
        nullable=True,
        comment="Reference to the last email in thread",
    )

    emails = relationship(
        "Email",
        back_populates="thread",
        foreign_keys="Email.thread_id",
        cascade="all, delete-orphan",
    )
    first_email = relationship(
        "Email",
        foreign_keys=[first_email_id],
        post_update=True,
    )
    last_email = relationship(
        "Email",
        foreign_keys=[last_email_id],
        post_update=True,
    )

    __table_args__ = (
        Index("idx_thread_subject_created", "subject", "created_at"),
        Index("idx_thread_updated", "updated_at"),
    )


class RawEmail(Base):
    """Model for storing raw email data received from webhooks."""

    __tablename__ = "emails_raw"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_json = Column(Text, comment="Base64 encoded JSON data")
    processing_status = Column(
        Enum(ProcessingStatus, name="processingstatus", create_type=False),
        default=ProcessingStatus.PENDING,
        index=True,
    )
    error_message = Column(Text, nullable=True)
    mailbox_hash = Column(String(100), nullable=True, index=True)


class Email(Base):
    """Model for processed email data."""

    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    raw_email_id = Column(Integer, ForeignKey("emails_raw.id"), nullable=False)
    thread_id = Column(
        Integer,
        ForeignKey("email_threads.id"),
        nullable=True,
        index=True,
        comment="Reference to the email thread",
    )

    message_id = Column(String(255), unique=True, index=True, nullable=False)
    message_stream = Column(String(100), nullable=True)

    from_email = Column(String(320), nullable=False, index=True)
    from_name = Column(String(255), nullable=True)

    subject = Column(String(998), nullable=True, index=True)
    text_body = Column(Text, nullable=True, comment="Plain text body")
    html_body = Column(Text, nullable=True, comment="HTML body")
    stripped_text_reply = Column(Text, nullable=True, comment="Stripped text reply")

    sent_at = Column(DateTime(timezone=True), nullable=True, index=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

    mailbox_hash = Column(String(100), nullable=True, index=True)
    tag = Column(String(255), nullable=True, index=True)
    original_recipient = Column(String(320), nullable=True)
    reply_to = Column(String(320), nullable=True)

    parent_email_id = Column(
        Integer,
        ForeignKey("emails.id"),
        nullable=True,
        index=True,
        comment="Legacy parent email link (kept for migration)",
    )
    parent_email_identifier = Column(
        Text,
        nullable=True,
        index=True,
        comment="Parent Email Identifier : In-Reply-To or References Headers",
    )
    email_identifier = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Email Identifier : X-Microsoft-Original-Message-ID or X-Gmail-Original-Message-ID Headers",
    )

    thread_position = Column(
        Integer, default=0, nullable=False, comment="Position of email in thread"
    )

    spam_score = Column(Float, nullable=True, index=True)
    spam_status = Column(
        Enum(SpamStatus, name="spamstatus", create_type=False),
        default=SpamStatus.UNKNOWN,
        nullable=False,
        index=True,
    )

    actionables_processing_status = Column(
        Enum(
            ActionablesProcessingStatus,
            name="actionablesprocessingstatus",
            create_type=False,
        ),
        default=ActionablesProcessingStatus.PENDING,
        nullable=False,
        index=True,
        comment="Status of actionables processing for this email",
    )
    actionables_processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when actionables processing was completed",
    )
    actionables_error_message = Column(
        Text,
        nullable=True,
        comment="Error message if actionables processing failed",
    )

    user = relationship("User")
    raw_email_entry = relationship(
        "RawEmail",
        backref="parsed_email",
    )
    thread = relationship(
        "EmailThread",
        back_populates="emails",
        foreign_keys=[thread_id],
    )
    recipients = relationship(
        "EmailRecipient",
        back_populates="email",
        cascade="all, delete-orphan",
    )
    attachments = relationship(
        "EmailAttachment",
        back_populates="email",
        cascade="all, delete-orphan",
    )
    headers = relationship(
        "EmailHeader",
        back_populates="email",
        cascade="all, delete-orphan",
    )
    parent_email = relationship(
        "Email",
        remote_side=[id],
        backref="child_emails",
        foreign_keys=[parent_email_id],
    )

    __table_args__ = (
        Index("idx_email_from_sent", "from_email", "sent_at"),
        Index("idx_email_subject_sent", "subject", "sent_at"),
        Index("idx_email_mailbox_sent", "mailbox_hash", "sent_at"),
        Index("idx_email_original_recipient_sent", "original_recipient", "sent_at"),
        Index("idx_email_reply_to_sent", "reply_to", "sent_at"),
        Index("idx_email_thread_position", "thread_id", "thread_position"),
        Index("idx_email_user_id", "user_id"),
    )


class EmailRecipient(Base):
    """Model for email recipients (to, cc, bcc, from)."""

    __tablename__ = "email_recipients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)
    recipient_type = Column(
        Enum(RecipientType, name="recipienttype", create_type=False),
        index=True,
        nullable=False,
    )
    email_address = Column(String(320), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    mailbox_hash = Column(String(100), nullable=True)

    email = relationship("Email", back_populates="recipients")


class EmailAttachment(Base):
    """Model for email attachments."""

    __tablename__ = "email_attachments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    content_type = Column(String(127), nullable=False)
    content_length = Column(Integer, nullable=False)
    content_id = Column(String(255), nullable=True)
    file_path = Column(String(512), nullable=False)
    file_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    email = relationship("Email", back_populates="attachments")

    __table_args__ = (Index("idx_attachment_email_filename", "email_id", "filename"),)


class EmailHeader(Base):
    """Model for email headers."""

    __tablename__ = "email_headers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=True)

    email = relationship("Email", back_populates="headers")

    __table_args__ = (
        Index("idx_header_name_value", "name", "value"),
        Index("idx_header_email_id_name", "email_id", "name"),
    )
