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
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    sent_emails = relationship("SentEmail", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"


class SentEmail(Base):
    __tablename__ = "sent_emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email_id = Column(String)
    from_email = Column(String, nullable=False)
    to_email = Column(String, nullable=False)
    api_key = Column(String)

    status = Column(
        Enum(EmailSendStatus, name="emailsendstatus", create_type=False),
        default=EmailSendStatus.PENDING,
        index=True,
    )
    error_code = Column(Integer)
    message = Column(Text)
    message_id = Column(String)
    submitted_at = Column(DateTime(timezone=True))

    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)
    postmark_error_code = Column(Integer)
    is_silent_failure = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="sent_emails")

    def __repr__(self) -> str:
        return (
            f"<SentEmail(id={self.id}, user_id={self.user_id}, status='{self.status}')>"
        )
