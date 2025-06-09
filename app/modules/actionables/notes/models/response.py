from typing import List, Literal

from pydantic import BaseModel, Field

from app.modules.actionables.notes.models.request import CreateNoteModel


class NoteCreation(BaseModel):
    type: Literal["note"] = "note"
    data: CreateNoteModel


class NoteAction(BaseModel):
    """The action to be taken by the notes agent."""

    action: NoteCreation = Field(..., discriminator="type")


class NotesAgentResponse(BaseModel):
    """The response from the notes agent, containing a list of actions."""

    actions: List[NoteAction]
