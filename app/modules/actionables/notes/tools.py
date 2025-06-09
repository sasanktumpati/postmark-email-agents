from dataclasses import dataclass

from pydantic_ai import RunContext

from app.core.db.database import get_db_session
from app.modules.actionables.notes.db import EmailNote
from app.modules.actionables.notes.models.request import CreateNoteModel
from app.modules.actionables.notes.repo import NotesRepository


@dataclass
class NotesDependencies:
    email_id: int


async def create_note(
    ctx: RunContext[NotesDependencies], note_data: CreateNoteModel
) -> str:
    """Create a note based on the email content."""
    async with get_db_session() as session:
        repo = NotesRepository(session)
        await repo.note.create(
            EmailNote(email_id=ctx.deps.email_id, note=note_data.note)
        )
        await repo.commit()
        return "Note created successfully."
