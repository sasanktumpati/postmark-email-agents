from app.core.db.repository import Repository
from app.modules.actionables.notes.db import EmailNote


class NotesRepository:
    def __init__(self):
        self.note = Repository(EmailNote)

    async def commit(self):
        await self.db_session.commit()
