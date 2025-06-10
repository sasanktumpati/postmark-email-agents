from app.core.db.repository import Repository
from app.modules.actionables.shopping.db import Bill, Coupon


class ShoppingRepository:
    def __init__(self):
        self.bill = Repository(Bill)
        self.coupon = Repository(Coupon)

    async def commit(self):
        await self.db_session.commit()
