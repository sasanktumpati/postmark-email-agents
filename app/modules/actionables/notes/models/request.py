from pydantic import BaseModel, Field


class CreateNoteModel(BaseModel):
    """Tool call model for creating a note."""

    note: str = Field(..., description="The content of the note.")
