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


class Priority(enum.Enum):
    """Enum for priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Currency(enum.Enum):
    """Enum for currency types."""

    INR = "INR"
    USD = "USD"
    EUR = "EUR"


class BillCategory(enum.Enum):
    """Enum for bill categories."""

    UTILITY = "utility"
    SUBSCRIPTION = "subscription"
    SHOPPING = "shopping"
    INSURANCE = "insurance"
    LOAN = "loan"
    CREDIT_CARD = "credit_card"
    OTHER = "other"


class CouponCategory(enum.Enum):
    """Enum for coupon categories."""

    SHOPPING = "shopping"
    FOOD = "food"
    TRAVEL = "travel"
    ENTERTAINMENT = "entertainment"
    SERVICES = "services"
    OTHER = "other"


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
    description = Column(Text, nullable=True)
    category = Column(Enum(BillCategory), default=BillCategory.OTHER)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)

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
    offer_url = Column(String(512), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(CouponCategory), default=CouponCategory.OTHER)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = relationship("Email", backref="coupons")
