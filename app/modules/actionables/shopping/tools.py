from dataclasses import dataclass

from pydantic_ai import RunContext

from app.core.db.database import get_db_session
from app.modules.actionables.shopping.db import Bill, Coupon
from app.modules.actionables.shopping.models.request import (
    SaveBillModel,
    SaveCouponModel,
)
from app.modules.actionables.shopping.repo import ShoppingRepository


@dataclass
class ShoppingDependencies:
    email_id: int


async def save_bill(
    ctx: RunContext[ShoppingDependencies], bill_data: SaveBillModel
) -> str:
    """Save a bill from an email."""
    async with get_db_session() as session:
        repo = ShoppingRepository(session)
        await repo.bill.create(
            Bill(
                email_id=ctx.deps.email_id,
                vendor=bill_data.vendor,
                amount=bill_data.amount,
                currency=bill_data.currency,
                due_date=bill_data.due_date,
                payment_url=bill_data.payment_url,
            )
        )
        await repo.commit()
        return f"Bill from {bill_data.vendor} for {bill_data.amount} saved."


async def save_coupon(
    ctx: RunContext[ShoppingDependencies], coupon_data: SaveCouponModel
) -> str:
    """Save a coupon from an email."""
    async with get_db_session() as session:
        repo = ShoppingRepository(session)
        await repo.coupon.create(
            Coupon(
                email_id=ctx.deps.email_id,
                vendor=coupon_data.vendor,
                code=coupon_data.code,
                discount=coupon_data.discount,
                expiry_date=coupon_data.expiry_date,
            )
        )
        await repo.commit()
        return f"Coupon from {coupon_data.vendor} with code {coupon_data.code} saved."
