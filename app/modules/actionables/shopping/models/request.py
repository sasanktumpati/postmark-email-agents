from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.actionables.shopping.db import Currency


class SaveBillModel(BaseModel):
    """Tool call model for saving a bill."""

    vendor: str = Field(..., description="The vendor from whom the bill is.")
    amount: float = Field(..., description="The amount of the bill.")
    currency: Optional[Currency] = Field(
        Currency.USD, description="The currency of the bill."
    )
    due_date: Optional[datetime] = Field(None, description="The due date of the bill.")
    payment_url: Optional[str] = Field(None, description="The URL to pay the bill.")


class SaveCouponModel(BaseModel):
    """Tool call model for saving a coupon."""

    vendor: str = Field(..., description="The vendor for which the coupon is valid.")
    code: str = Field(..., description="The coupon code.")
    discount: Optional[str] = Field(None, description="Description of the discount.")
    expiry_date: Optional[datetime] = Field(
        None, description="The expiry date of the coupon."
    )
