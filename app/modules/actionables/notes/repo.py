from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.repository import TransactionalRepository
from app.modules.actionables.notes.db import EmailNote


class NotesRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.note = TransactionalRepository(db_session, EmailNote)

    async def commit(self):
        await self.db_session.commit()
