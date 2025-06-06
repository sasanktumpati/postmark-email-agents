import enum

from sqlalchemy import (
    JSON,
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


class RecipientTypeEnum(enum.Enum):
    """Enum for recipient types in emails."""

    FROM = "from"
    TO = "to"
    CC = "cc"
    BCC = "bcc"


class ProcessingStatusEnum(enum.Enum):
    """Enum for processing status of raw emails."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class SpamStatusEnum(enum.Enum):
    """Enum for spam status of emails."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class EmailsRaw(Base):
    __tablename__ = "emails_raw"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_json = Column(JSON)
    processing_status = Column(
        Enum(ProcessingStatusEnum), default=ProcessingStatusEnum.PENDING, index=True
    )
    error_message = Column(Text, nullable=True)
    mailbox_hash = Column(String(100), nullable=True, index=True)


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    raw_email_id = Column(Integer, ForeignKey("emails_raw.id"), nullable=False)

    message_id = Column(String(255), unique=True, index=True, nullable=False)
    message_stream = Column(String(100), nullable=True)

    from_email = Column(String(320), nullable=False, index=True)
    from_name = Column(String(255), nullable=True)

    subject = Column(String(998), nullable=True, index=True)
    text_body = Column(Text, nullable=True)
    html_body = Column(Text, nullable=True)
    stripped_text_reply = Column(Text, nullable=True)

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
        comment="Self-referencing parent email link",
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

    spam_score = Column(Float, nullable=True, index=True)
    spam_status = Column(
        Enum(SpamStatusEnum),
        default=SpamStatusEnum.UNKNOWN,
        nullable=False,
        index=True,
    )

    raw_email_entry = relationship(
        "EmailsRaw",
        backref="parsed_email",
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
    )


class EmailRecipient(Base):
    __tablename__ = "email_recipients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    recipient_type = Column(Enum(RecipientTypeEnum), index=True, nullable=False)
    email_address = Column(String(320), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    mailbox_hash = Column(String(100), nullable=True)

    email = relationship("Email", back_populates="recipients")


class EmailAttachment(Base):
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
