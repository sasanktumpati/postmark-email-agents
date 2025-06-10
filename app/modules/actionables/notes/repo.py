from app.core.db.repository import Repository
from app.core.logger import get_logger
from app.modules.actionables.notes.db import EmailNote

logger = get_logger(__name__)


class NotesRepository:
    def __init__(self):
        logger.debug("Initializing NotesRepository.")
        self.note = Repository(EmailNote)

    async def commit(self):
        await self.db_session.commit()
