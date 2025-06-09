from typing import List, Literal, Union

from pydantic import BaseModel, Field

from .request import SaveBillModel, SaveCouponModel


class BillCreation(BaseModel):
    type: Literal["bill"] = "bill"
    data: SaveBillModel


class CouponCreation(BaseModel):
    type: Literal["coupon"] = "coupon"
    data: SaveCouponModel


class ShoppingAction(BaseModel):
    """The action to be taken by the shopping agent."""

    action: Union[BillCreation, CouponCreation] = Field(..., discriminator="type")


class ShoppingAgentResponse(BaseModel):
    """The response from the shopping agent, containing a list of actions."""

    actions: List[ShoppingAction]
