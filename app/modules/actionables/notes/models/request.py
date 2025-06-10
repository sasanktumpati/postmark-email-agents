from typing import Optional

from pydantic import BaseModel, Field

from app.modules.actionables.notes.db import NoteCategory, Priority


class CreateNoteModel(BaseModel):
    """Tool call model for creating a note from email content."""

    title: Optional[str] = Field(
        None,
        description="Clear, descriptive title for the note that summarizes the main topic or subject.",
    )
    note: str = Field(
        ...,
        description="Detailed note content that captures key information, decisions, insights, or important points from the email. Should be comprehensive yet concise, including relevant context and actionable items.",
    )
    category: NoteCategory = Field(
        NoteCategory.GENERAL,
        description="Category of the note: general for misc info, meeting for meeting-related content, task for actionable items, idea for concepts/proposals, decision for choices made, contact for people/company info, information for reference data.",
    )
    priority: Priority = Field(
        Priority.MEDIUM,
        description="Priority level: urgent for critical information, high for important reference, medium for useful notes, low for nice-to-have information.",
    )
