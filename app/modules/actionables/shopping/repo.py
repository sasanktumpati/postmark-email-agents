from app.core.db.repository import Repository
from app.core.logger import get_logger
from app.modules.actionables.shopping.db import Bill, Coupon

logger = get_logger(__name__)


class ShoppingRepository:
    def __init__(self):
        logger.debug("Initializing ShoppingRepository.")
        self.bill = Repository(Bill)
        self.coupon = Repository(Coupon)

    async def commit(self):
        await self.db_session.commit()
