import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.db.database import Base


class EmailSendStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    mailbox_hash = Column(String(100), index=True)
    api_key = Column(String, unique=True, index=True)
    api_key_created_at = Column(DateTime, default=func.now())
    failed_auth_attempts = Column(Integer, default=0)
    last_failed_auth_at = Column(DateTime)
    first_login_at = Column(DateTime)
    last_successful_auth_at = Column(DateTime)
    account_locked_until = Column(DateTime)
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    sent_emails = relationship("SentEmail", back_populates="user")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_mailbox_active", "mailbox_hash", "is_active"),
        Index(
            "ix_users_failed_attempts", "failed_auth_attempts", "account_locked_until"
        ),
        Index("ix_users_login_tracking", "first_login_at", "last_successful_auth_at"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"


class SentEmail(Base):
    __tablename__ = "sent_emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, index=True)
    from_email = Column(String, nullable=False, index=True)
    to_email = Column(String, nullable=False, index=True)
    api_key = Column(String, index=True)

    status = Column(
        Enum(EmailSendStatus, name="emailsendstatus", create_type=False),
        default=EmailSendStatus.PENDING,
        index=True,
    )
    error_code = Column(Integer, index=True)
    message = Column(Text)
    message_id = Column(String, index=True)
    submitted_at = Column(DateTime(timezone=True), index=True)

    retry_count = Column(Integer, default=0, index=True)
    last_retry_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)
    postmark_error_code = Column(Integer)
    is_silent_failure = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="sent_emails")

    __table_args__ = (
        Index("ix_sent_emails_user_status", "user_id", "status"),
        Index("ix_sent_emails_user_created", "user_id", "created_at"),
        Index("ix_sent_emails_status_retry", "status", "retry_count"),
    )

    def __repr__(self) -> str:
        return (
            f"<SentEmail(id={self.id}, user_id={self.user_id}, status='{self.status}')>"
        )
