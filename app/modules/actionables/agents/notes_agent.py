from pydantic_ai import Agent

from app.core.config import settings
from app.modules.actionables.notes.models.response import NotesAgentResponse
from app.modules.actionables.notes.tools import (
    NotesDependencies,
    create_note,
)

notes_system_prompt = """
You are an intelligent assistant that creates notes from email content.
Your task is to analyze an email thread and identify key information or summaries that should be saved as notes.
An email might contain multiple distinct topics that should be saved as separate notes.

- Extract the core information to create a concise and informative note.
- If the email thread has a clear summary, use that for the note.
- If not, create a summary of the important points.

You must return a list of all notes to be created.
"""

notes_agent = Agent(
    model=settings.gemini_model,
    deps_type=NotesDependencies,
    output_type=NotesAgentResponse,
    system_prompt=notes_system_prompt,
    tools=[create_note],
    retries=3,
    output_retries=3,
)
