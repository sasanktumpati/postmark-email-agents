from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.repository import TransactionalRepository
from app.modules.actionables.shopping.db import Bill, Coupon


class ShoppingRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.bill = TransactionalRepository(db_session, Bill)
        self.coupon = TransactionalRepository(db_session, Coupon)

    async def commit(self):
        await self.db_session.commit()
