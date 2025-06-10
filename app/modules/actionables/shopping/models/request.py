from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.actionables.shopping.db import (
    BillCategory,
    CouponCategory,
    Currency,
    Priority,
)


class SaveBillModel(BaseModel):
    """Tool call model for saving a bill from email content."""

    vendor: str = Field(
        ..., description="Name of the company or vendor that issued the bill."
    )
    amount: float = Field(..., description="Total amount due for the bill.")
    currency: Currency = Field(Currency.USD, description="Currency of the bill amount.")
    due_date: Optional[datetime] = Field(
        None,
        description="Due date for payment in ISO format. Extract from email or use reasonable default if not specified.",
    )
    payment_url: Optional[str] = Field(
        None,
        description="Direct URL or link for making payment, if provided in the email.",
    )
    description: Optional[str] = Field(
        None,
        description="Brief description of what the bill is for - service period, account details, or bill type. Should provide context for the charge.",
    )
    category: BillCategory = Field(
        BillCategory.OTHER,
        description="Category of bill: utility for electricity/water/gas, subscription for recurring services, shopping for purchases, insurance for policies, loan for payments, credit_card for statements, other for miscellaneous.",
    )
    priority: Priority = Field(
        Priority.MEDIUM,
        description="Priority level: urgent for overdue/critical payments, high for important bills, medium for regular bills, low for optional payments.",
    )


class SaveCouponModel(BaseModel):
    """Tool call model for saving a coupon from email content."""

    vendor: str = Field(
        ..., description="Name of the company or store offering the coupon."
    )
    code: str = Field(..., description="Coupon code or promo code to use for discount.")
    discount: Optional[str] = Field(
        None,
        description="Description of the discount offered - percentage off, dollar amount, or specific offer details.",
    )
    offer_url: Optional[str] = Field(
        None,
        description="Direct URL or link to claim the offer or promotion, if provided in the email.",
    )
    expiry_date: Optional[datetime] = Field(
        None,
        description="Expiration date of the coupon in ISO format, if specified in the email.",
    )
    description: Optional[str] = Field(
        None,
        description="Additional details about the coupon - minimum purchase requirements, applicable products, terms and conditions, or usage restrictions.",
    )
    category: CouponCategory = Field(
        CouponCategory.OTHER,
        description="Category of coupon: shopping for retail discounts, food for restaurant/grocery, travel for booking discounts, entertainment for events/streaming, services for professional services, other for miscellaneous.",
    )
    priority: Priority = Field(
        Priority.LOW,
        description="Priority level: urgent for limited-time offers, high for significant savings, medium for good deals, low for standard promotions.",
    )
