import base64
import json
import logging
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from .db import (
    Email,
    EmailAttachment,
    EmailHeader,
    EmailRecipient,
    EmailsRaw,
    ProcessingStatusEnum,
    RecipientTypeEnum,
    SpamStatusEnum,
)
from .models import AttachmentModel, HeaderModel, PostmarkInboundEmail


class EmailWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.attachments_dir = Path("attachments")
        self.attachments_dir.mkdir(exist_ok=True)

    def _encode_to_base64(self, data: str) -> str:
        """Encode string data to base64."""
        if not data:
            return ""
        return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    def _decode_from_base64(self, data: str) -> str:
        """Decode base64 string data."""
        if not data:
            return ""
        try:
            return base64.b64decode(data.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logging.error(f"Failed to decode base64 data: {str(e)}")
            return ""

    def _prepare_raw_json(self, raw_data: Dict) -> str:
        """Convert raw email data to base64-encoded JSON string."""
        try:
            json_string = json.dumps(raw_data, ensure_ascii=False)
            return self._encode_to_base64(json_string)
        except Exception as e:
            raise ValueError(f"Failed to prepare raw JSON data: {str(e)}")

    async def save_raw_email(self, raw_data: Dict) -> EmailsRaw:
        """Saves raw email data to the database."""
        try:
            raw_json_b64 = self._prepare_raw_json(raw_data)

            raw_email = EmailsRaw(
                raw_json=raw_json_b64,
                processing_status=ProcessingStatusEnum.PENDING,
                mailbox_hash=raw_data.get("MailboxHash", ""),
            )
            self.db.add(raw_email)
            await self.db.commit()
            await self.db.refresh(raw_email)
            return raw_email
        except Exception as e:
            await self.db.rollback()
            raise Exception(f"Failed to save raw email: {str(e)}")

    def validate_webhook_request(self, data: Dict) -> PostmarkInboundEmail:
        """Validate the webhook request against the Pydantic model."""
        try:
            return PostmarkInboundEmail(**data)
        except Exception as e:
            raise ValueError(f"Invalid webhook data: {str(e)}")

    def extract_email_identifier(self, headers: List[HeaderModel]) -> str:
        """Extract unique email identifier from headers."""

        for header in headers:
            name = header.Name.lower()
            if name in [
                "x-microsoft-original-message-id",
                "x-gmail-original-message-id",
            ]:
                if header.Value:
                    return header.Value.strip()

        for header in headers:
            if header.Name.lower() == "message-id":
                if header.Value:
                    return header.Value.strip()

        return f"generated-{uuid.uuid4()}"

    def extract_parent_email_identifier(
        self, headers: List[HeaderModel]
    ) -> Optional[str]:
        """Extract parent email identifier from In-Reply-To or References headers."""
        for header in headers:
            name = header.Name.lower()
            if name in ["in-reply-to", "references"]:
                if header.Value:
                    return header.Value.strip()
        return None

    def parse_spam_status(
        self, headers: List[HeaderModel]
    ) -> Tuple[Optional[float], SpamStatusEnum]:
        """Parse spam score and status from headers."""
        spam_score = None
        spam_status = SpamStatusEnum.UNKNOWN

        for header in headers:
            name = header.Name.lower()
            value = header.Value

            if "spam" in name and "score" in name:
                try:
                    spam_score = float(value)
                except Exception:
                    pass

            if "spam" in name and "status" in name:
                if value.lower() == "yes":
                    spam_status = SpamStatusEnum.YES
                elif value.lower() == "no":
                    spam_status = SpamStatusEnum.NO

        return spam_score, spam_status

    async def save_attachments(
        self, attachments: List[AttachmentModel], email_id: int
    ) -> List[EmailAttachment]:
        """Save email attachments to filesystem and database."""
        saved_attachments = []
        email_dir = self.attachments_dir / str(email_id)
        try:
            email_dir.mkdir(exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create directory for attachments: {str(e)}")
            return saved_attachments
        for attachment in attachments:
            try:
                content_bytes = base64.b64decode(attachment.Content)
                file_extension = ""
                if attachment.Name and "." in attachment.Name:
                    file_extension = Path(attachment.Name).suffix
                elif attachment.ContentType:
                    content_type_map = {
                        "image/jpeg": ".jpg",
                        "image/png": ".png",
                        "image/gif": ".gif",
                        "application/pdf": ".pdf",
                        "text/plain": ".txt",
                        "application/msword": ".doc",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                        "application/vnd.ms-excel": ".xls",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                    }
                    file_extension = content_type_map.get(attachment.ContentType)
                    if file_extension is None:
                        guessed_extension = mimetypes.guess_extension(
                            attachment.ContentType
                        )
                        if guessed_extension:
                            file_extension = guessed_extension
                        else:
                            logging.warning(
                                f"Could not determine file extension for ContentType: {attachment.ContentType}, using no extension."
                            )
                            file_extension = ""
                else:
                    logging.warning(
                        "Attachment has no name and no ContentType, saving without extension."
                    )
                    file_extension = ""
                unique_filename = (
                    f"{uuid.uuid4().hex}_{Path(attachment.Name).stem}{file_extension}"
                )
                file_path = email_dir / unique_filename
                try:
                    with open(file_path, "wb") as f:
                        f.write(content_bytes)
                except Exception as e:
                    logging.error(
                        f"Failed to write attachment file {file_path}: {str(e)}"
                    )
                    continue
                db_attachment = EmailAttachment(
                    email_id=email_id,
                    filename=attachment.Name,
                    content_type=attachment.ContentType,
                    content_length=attachment.ContentLength,
                    content_id=attachment.ContentID,
                    file_path=str(file_path),
                    file_url=f"/attachments/{email_id}/{unique_filename}",
                )
                try:
                    self.db.add(db_attachment)
                    saved_attachments.append(db_attachment)
                except Exception as e:
                    logging.error(f"Failed to add attachment to db: {str(e)}")
                    continue
            except Exception as e:
                logging.error(
                    f"Failed to save attachment {getattr(attachment, 'Name', 'unknown')}: {str(e)}"
                )
                continue
        return saved_attachments

    async def save_recipients(
        self, email_data: PostmarkInboundEmail, email_id: int
    ) -> List[EmailRecipient]:
        """Save email recipients to database."""
        recipients = []

        if email_data.FromFull:
            from_recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientTypeEnum.FROM,
                email_address=email_data.FromFull.Email,
                name=email_data.FromFull.Name,
                mailbox_hash=email_data.FromFull.MailboxHash,
            )
            recipients.append(from_recipient)

        for to_recipient in email_data.ToFull or []:
            recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientTypeEnum.TO,
                email_address=to_recipient.Email,
                name=to_recipient.Name,
                mailbox_hash=to_recipient.MailboxHash,
            )
            recipients.append(recipient)

        for cc_recipient in email_data.CcFull or []:
            recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientTypeEnum.CC,
                email_address=cc_recipient.Email,
                name=cc_recipient.Name,
                mailbox_hash=cc_recipient.MailboxHash,
            )
            recipients.append(recipient)

        for bcc_recipient in email_data.BccFull or []:
            recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientTypeEnum.BCC,
                email_address=bcc_recipient.Email,
                name=bcc_recipient.Name,
                mailbox_hash=bcc_recipient.MailboxHash,
            )
            recipients.append(recipient)

        for recipient in recipients:
            self.db.add(recipient)

        return recipients

    async def save_headers(
        self, headers: List[HeaderModel], email_id: int
    ) -> List[EmailHeader]:
        """Save email headers to database."""
        db_headers = []

        for header in headers:
            db_header = EmailHeader(
                email_id=email_id,
                name=header.Name,
                value=header.Value,
            )
            self.db.add(db_header)
            db_headers.append(db_header)

        return db_headers

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into a datetime object."""
        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.now(datetime.timezone.utc)

    async def get_parent_email_id(
        self, parent_identifier: Optional[str]
    ) -> Optional[int]:
        """Find the parent email's id by its email_identifier."""
        if not parent_identifier:
            return None
        from sqlalchemy import select

        result = await self.db.execute(
            select(Email.id).where(Email.email_identifier == parent_identifier)
        )
        row = result.first()
        return row[0] if row else None

    async def check_duplicate_email(
        self, message_id: str, email_identifier: str
    ) -> Optional[Email]:
        """Check if an email with the same message_id or email_identifier already exists."""
        from sqlalchemy import or_, select

        result = await self.db.execute(
            select(Email).where(
                or_(
                    Email.message_id == message_id,
                    Email.email_identifier == email_identifier,
                )
            )
        )
        return result.scalar_one_or_none()

    async def process_webhook_email(
        self, raw_email: EmailsRaw, email_data: PostmarkInboundEmail
    ) -> Email:
        """Process the validated email data and save to database."""
        try:
            email_identifier = self.extract_email_identifier(email_data.Headers)
            parent_identifier = self.extract_parent_email_identifier(email_data.Headers)
            spam_score, spam_status = self.parse_spam_status(email_data.Headers)
            sent_at = self.parse_date(email_data.Date)

            parent_email_id = await self.get_parent_email_id(parent_identifier)

            text_body_b64 = (
                self._encode_to_base64(email_data.TextBody)
                if email_data.TextBody
                else None
            )
            html_body_b64 = (
                self._encode_to_base64(email_data.HtmlBody)
                if email_data.HtmlBody
                else None
            )
            stripped_text_reply_b64 = (
                self._encode_to_base64(email_data.StrippedTextReply)
                if email_data.StrippedTextReply
                else None
            )

            email = Email(
                raw_email_id=raw_email.id,
                message_id=email_data.MessageID,
                message_stream=email_data.MessageStream,
                from_email=email_data.From,
                from_name=email_data.FromName,
                subject=email_data.Subject,
                text_body=text_body_b64,
                html_body=html_body_b64,
                stripped_text_reply=stripped_text_reply_b64,
                sent_at=sent_at,
                mailbox_hash=email_data.MailboxHash,
                tag=email_data.Tag,
                original_recipient=email_data.OriginalRecipient,
                reply_to=email_data.ReplyTo,
                parent_email_identifier=parent_identifier,
                parent_email_id=parent_email_id,
                email_identifier=email_identifier,
                spam_score=spam_score,
                spam_status=spam_status,
            )

            self.db.add(email)
            await self.db.flush()
            await self.save_recipients(email_data, email.id)
            await self.save_attachments(email_data.Attachments or [], email.id)
            await self.save_headers(email_data.Headers, email.id)
            await self.db.commit()
            await self.db.refresh(email)
            return email
        except Exception as e:
            await self.db.rollback()
            raise Exception(f"Failed to process webhook email: {str(e)}")

    async def process_postmark_webhook(self, raw_data: Dict) -> Dict[str, str]:
        """Process the Postmark webhook data."""

        try:
            email_data = self.validate_webhook_request(raw_data)
        except Exception as e:
            raise ValueError(f"Invalid webhook data: {str(e)}")

        message_id = email_data.MessageID
        email_identifier = self.extract_email_identifier(email_data.Headers)

        existing_email = await self.check_duplicate_email(message_id, email_identifier)
        if existing_email:
            logging.info(
                f"Duplicate email detected: message_id={message_id}, "
                f"email_identifier={email_identifier}, existing_email_id={existing_email.id}"
            )

            from sqlalchemy import func, select

            attachments_count_result = await self.db.execute(
                select(func.count(EmailAttachment.id)).where(
                    EmailAttachment.email_id == existing_email.id
                )
            )
            attachments_count = attachments_count_result.scalar() or 0

            return {
                "email_id": str(existing_email.id),
                "raw_email_id": str(existing_email.raw_email_id),
                "message_id": existing_email.message_id,
                "attachments_count": str(attachments_count),
                "duplicate": "true",
            }

        logging.info(
            f"Processing new email: message_id={message_id}, email_identifier={email_identifier}"
        )
        raw_email = await self.save_raw_email(raw_data)
        try:
            email = await self.process_webhook_email(raw_email, email_data)

            attachments_count = len(email_data.Attachments or [])

            return {
                "email_id": str(email.id),
                "raw_email_id": str(raw_email.id),
                "message_id": email.message_id,
                "attachments_count": str(attachments_count),
                "duplicate": "false",
            }
        except Exception as e:
            raw_email.processing_status = ProcessingStatusEnum.FAILED
            raw_email.error_message = str(e)
            await self.db.commit()
            raise


async def get_email_service(db: AsyncSession) -> EmailWebhookService:
    return EmailWebhookService(db)
