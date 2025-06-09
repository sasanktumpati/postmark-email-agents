import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Currency(enum.Enum):
    """Enum for currency types."""

    INR = "INR"
    USD = "USD"
    EUR = "EUR"


class Bill(Base):
    """Model for bills extracted from emails."""

    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    vendor = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(Currency), default=Currency.USD)
    due_date = Column(DateTime(timezone=True), nullable=True)
    payment_url = Column(String(512), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = relationship("Email", backref="bills")


class Coupon(Base):
    """Model for coupons extracted from emails."""

    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    vendor = Column(String(255), nullable=False)
    code = Column(String(100), nullable=False)
    discount = Column(Text, nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = relationship("Email", backref="coupons")
