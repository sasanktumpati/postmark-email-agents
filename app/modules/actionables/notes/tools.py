from dataclasses import dataclass

from pydantic_ai import RunContext

from app.core.db.database import get_db_transaction
from app.core.logger import get_logger
from app.modules.actionables.notes.db import EmailNote
from app.modules.actionables.notes.models.request import CreateNoteModel
from app.modules.actionables.notes.repo import NotesRepository

logger = get_logger(__name__)


@dataclass
class NotesDependencies:
    email_id: int


async def create_note(
    ctx: RunContext[NotesDependencies], note_data: CreateNoteModel
) -> str:
    """Create a note based on the email content."""
    logger.info(
        f"TOOL CALLED: create_note for email_id {ctx.deps.email_id} with data: {note_data}"
    )

    try:
        repo = NotesRepository()
        async with get_db_transaction() as session:
            note = await repo.note.create(
                session,
                EmailNote(
                    email_id=ctx.deps.email_id,
                    note=note_data.note,
                    title=note_data.title,
                    category=note_data.category,
                    priority=note_data.priority,
                ),
            )
            logger.info(f"Created note with ID: {note.id}")

            result = f"Note '{note_data.title or 'Untitled'}' created successfully in {note_data.category.value} category with {note_data.priority.value} priority."
            logger.info(f"TOOL SUCCESS: create_note - {result}")
            return result
    except Exception as e:
        logger.error(
            f"TOOL ERROR: create_note failed for email_id {ctx.deps.email_id}: {str(e)}",
            exc_info=True,
        )
        raise
