from dataclasses import dataclass

from pydantic_ai import RunContext

from app.core.db.database import get_db_transaction
from app.core.logger import get_logger
from app.modules.actionables.shopping.db import Bill, Coupon
from app.modules.actionables.shopping.models.request import (
    SaveBillModel,
    SaveCouponModel,
)
from app.modules.actionables.shopping.repo import ShoppingRepository

logger = get_logger(__name__)


@dataclass
class ShoppingDependencies:
    email_id: int


async def save_bill(
    ctx: RunContext[ShoppingDependencies], bill_data: SaveBillModel
) -> str:
    """Save a bill from an email."""
    logger.info(
        f"TOOL CALLED: save_bill for email_id {ctx.deps.email_id} with data: {bill_data}"
    )

    try:
        repo = ShoppingRepository()
        async with get_db_transaction() as session:
            bill = await repo.bill.create(
                session,
                Bill(
                    email_id=ctx.deps.email_id,
                    vendor=bill_data.vendor,
                    amount=bill_data.amount,
                    currency=bill_data.currency,
                    due_date=bill_data.due_date,
                    payment_url=bill_data.payment_url,
                    description=bill_data.description,
                    category=bill_data.category,
                    priority=bill_data.priority,
                ),
            )
            logger.info(f"Created bill with ID: {bill.id}")

            result = f"Bill from {bill_data.vendor} for {bill_data.amount} {bill_data.currency.value} saved in {bill_data.category.value} category with {bill_data.priority.value} priority."
            logger.info(f"TOOL SUCCESS: save_bill - {result}")
            return result
    except Exception as e:
        logger.error(
            f"TOOL ERROR: save_bill failed for email_id {ctx.deps.email_id}: {str(e)}",
            exc_info=True,
        )
        raise


async def save_coupon(
    ctx: RunContext[ShoppingDependencies], coupon_data: SaveCouponModel
) -> str:
    """Save a coupon from an email."""
    logger.info(
        f"TOOL CALLED: save_coupon for email_id {ctx.deps.email_id} with data: {coupon_data}"
    )

    try:
        repo = ShoppingRepository()
        async with get_db_transaction() as session:
            coupon = await repo.coupon.create(
                session,
                Coupon(
                    email_id=ctx.deps.email_id,
                    vendor=coupon_data.vendor,
                    code=coupon_data.code,
                    discount=coupon_data.discount,
                    expiry_date=coupon_data.expiry_date,
                    offer_url=coupon_data.offer_url,
                    description=coupon_data.description,
                    category=coupon_data.category,
                    priority=coupon_data.priority,
                ),
            )
            logger.info(f"Created coupon with ID: {coupon.id}")

            result = f"Coupon from {coupon_data.vendor} with code {coupon_data.code} saved in {coupon_data.category.value} category with {coupon_data.priority.value} priority."
            logger.info(f"TOOL SUCCESS: save_coupon - {result}")
            return result
    except Exception as e:
        logger.error(
            f"TOOL ERROR: save_coupon failed for email_id {ctx.deps.email_id}: {str(e)}",
            exc_info=True,
        )
        raise
