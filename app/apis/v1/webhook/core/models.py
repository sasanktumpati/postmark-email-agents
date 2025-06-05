from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class FromFullModel(BaseModel):
    Email: EmailStr
    Name: Optional[str] = None
    MailboxHash: Optional[str] = ""


class ToCcFullModel(BaseModel):
    Email: EmailStr
    Name: Optional[str] = None
    MailboxHash: Optional[str] = ""


class AttachmentModel(BaseModel):
    Name: str
    Content: str
    ContentType: str
    ContentLength: int
    ContentID: Optional[str] = None


class HeaderModel(BaseModel):
    Name: str
    Value: str


class PostmarkInboundEmail(BaseModel):
    From: EmailStr
    MessageStream: Optional[str] = "inbound"
    FromName: Optional[str] = None
    FromFull: FromFullModel
    To: Optional[str] = None
    ToFull: Optional[List[ToCcFullModel]] = Field(default_factory=list)
    Cc: Optional[str] = ""
    CcFull: Optional[List[ToCcFullModel]] = Field(default_factory=list)
    Bcc: Optional[str] = ""
    BccFull: Optional[List[ToCcFullModel]] = Field(default_factory=list)
    OriginalRecipient: Optional[str] = None
    ReplyTo: Optional[str] = ""
    Subject: Optional[str] = ""
    MessageID: str
    Date: str
    MailboxHash: Optional[str] = ""
    TextBody: Optional[str] = None
    HtmlBody: Optional[str] = None
    StrippedTextReply: Optional[str] = None
    Tag: Optional[str] = ""
    Headers: List[HeaderModel] = Field(default_factory=list)
    Attachments: Optional[List[AttachmentModel]] = Field(default_factory=list)
