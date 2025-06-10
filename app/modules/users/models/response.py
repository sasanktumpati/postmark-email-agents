from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserResponse(BaseModel):
    id: int
    name: Optional[str] = None
    email: EmailStr
    api_key: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SentEmailResponse(BaseModel):
    id: int
    user_id: int
    email_id: Optional[str] = None
    from_email: EmailStr
    to_email: EmailStr
    status: str
    error_code: Optional[int] = None
    message: Optional[str] = None
    message_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithSentEmailsResponse(UserResponse):
    sent_emails: List[SentEmailResponse] = []


class PostmarkEmailResponse(BaseModel):
    """Model for parsing Postmark API email response."""

    error_code: int = Field(alias="ErrorCode", default=0)
    message: Optional[str] = Field(alias="Message", default=None)
    message_id: Optional[str] = Field(alias="MessageID", default=None)
    submitted_at: Optional[datetime] = Field(alias="SubmittedAt", default=None)

    @field_validator("submitted_at", mode="before")
    @classmethod
    def parse_submitted_at(cls, v):
        if not v:
            return None

        if isinstance(v, str):
            try:
                if "." in v and v.endswith("Z"):
                    date_part, time_part = v[:-1].split(".")

                    time_part = time_part[:6]
                    v = f"{date_part}.{time_part}Z"

                if v.endswith("Z"):
                    return datetime.fromisoformat(v[:-1] + "+00:00")
                else:
                    return datetime.fromisoformat(v)
            except (ValueError, AttributeError):
                return None

        return v

    class Config:
        populate_by_name = True
        validate_by_name = True
