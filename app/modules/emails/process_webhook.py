import asyncio
import base64
import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.modules.users.users import (
    get_user_webhook_service,
)

from .models import (
    Email,
    EmailAttachment,
    EmailAttachmentData,
    EmailHeader,
    EmailHeaderData,
    EmailRecipient,
    PostmarkWebhookRequest,
    ProcessingStatus,
    RawEmail,
    RecipientType,
    SpamStatus,
)
from .thread_service import EmailThreadService

logger = get_logger(__name__)


class WebhookProcessingService:
    """Service for processing email webhooks from Postmark."""

    def __init__(self, db_session: AsyncSession, attachments_dir: Optional[str] = None):
        self.db = db_session
        self.attachments_dir = Path(attachments_dir or "attachments")
        self.attachments_dir.mkdir(exist_ok=True)
        self.thread_service = EmailThreadService(db_session)
        logger.debug("WebhookProcessingService initialized.")

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
            logger.error(f"Failed to decode base64 data: {str(e)}")
            return ""

    def _prepare_raw_json(self, raw_data: Dict) -> str:
        """Convert raw email data to base64-encoded JSON string."""
        try:
            json_string = json.dumps(raw_data, ensure_ascii=False)
            return self._encode_to_base64(json_string)
        except Exception as e:
            raise ValueError(f"Failed to prepare raw JSON data: {str(e)}")

    async def save_raw_email(self, raw_data: Dict) -> RawEmail:
        """Save raw email data to the database."""
        try:
            raw_json_b64 = self._prepare_raw_json(raw_data)

            raw_email = RawEmail(
                raw_json=raw_json_b64,
                processing_status=ProcessingStatus.PENDING,
                mailbox_hash=raw_data.get("MailboxHash", ""),
            )
            self.db.add(raw_email)
            await self.db.commit()
            await self.db.refresh(raw_email)
            logger.info(f"Raw email saved with ID: {raw_email.id}")
            return raw_email
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to save raw email: {str(e)}")
            raise Exception(f"Failed to save raw email: {str(e)}")

    def validate_webhook_request(self, data: Dict) -> PostmarkWebhookRequest:
        """Validate the webhook request against the Pydantic model."""
        try:
            return PostmarkWebhookRequest(**data)
        except Exception as e:
            logger.error(f"Invalid webhook data received: {str(e)}")
            raise ValueError(f"Invalid webhook data: {str(e)}")

    def extract_email_identifier(self, headers: List[EmailHeaderData]) -> str:
        """Extract unique email identifier from headers."""

        priority_headers = [
            "x-microsoft-original-message-id",
            "x-gmail-original-message-id",
            "message-id",
        ]

        for priority_header in priority_headers:
            for header in headers:
                if header.Name.lower() == priority_header and header.Value:
                    return header.Value.strip()

        generated_id = f"generated-{uuid.uuid4()}"
        logger.warning(
            f"No standard email identifier found in headers, generated: {generated_id}"
        )
        return generated_id

    def extract_parent_email_identifier(
        self, headers: List[EmailHeaderData]
    ) -> Optional[str]:
        """Extract parent email identifier from In-Reply-To or References headers."""
        for header in headers:
            name = header.Name.lower()
            if name in ["in-reply-to", "references"] and header.Value:
                return header.Value.strip()
        return None

    def parse_spam_status(
        self, headers: List[EmailHeaderData]
    ) -> Tuple[Optional[float], SpamStatus]:
        """Parse spam score and status from headers."""
        spam_score = None
        spam_status = SpamStatus.UNKNOWN

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
                    spam_status = SpamStatus.YES
                elif value.lower() == "no":
                    spam_status = SpamStatus.NO

        return spam_score, spam_status

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

        result = await self.db.execute(
            select(Email.id).where(Email.email_identifier == parent_identifier)
        )
        row = result.first()
        return row[0] if row else None

    async def check_duplicate_email(
        self, message_id: str, email_identifier: str
    ) -> Optional[Email]:
        """Check if an email with the same message_id or email_identifier already exists."""
        result = await self.db.execute(
            select(Email).where(
                or_(
                    Email.message_id == message_id,
                    Email.email_identifier == email_identifier,
                )
            )
        )
        email = result.scalar_one_or_none()
        if email:
            logger.warning(
                f"Duplicate email detected - message_id: {message_id}, email_identifier: {email_identifier}"
            )
        return email

    async def save_attachments(
        self, attachments: List[EmailAttachmentData], email_id: int
    ) -> List[EmailAttachment]:
        """Save email attachments to filesystem and database."""
        if not attachments:
            return []

        logger.debug(f"Saving {len(attachments)} attachments for email {email_id}")
        saved_attachments = []
        email_dir = self.attachments_dir / str(email_id)

        try:
            email_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory for attachments: {str(e)}")
            return saved_attachments

        for attachment in attachments:
            try:
                content_bytes = base64.b64decode(attachment.Content)

                file_extension = self._get_file_extension(attachment)

                unique_filename = (
                    f"{uuid.uuid4().hex}_{Path(attachment.Name).stem}{file_extension}"
                )
                file_path = email_dir / unique_filename

                try:
                    with open(file_path, "wb") as f:
                        f.write(content_bytes)
                except Exception as e:
                    logger.error(
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

                self.db.add(db_attachment)
                saved_attachments.append(db_attachment)

            except Exception as e:
                logger.error(f"Failed to save attachment {attachment.Name}: {str(e)}")
                continue

        return saved_attachments

    def _get_file_extension(self, attachment: EmailAttachmentData) -> str:
        """Determine file extension for attachment."""
        if attachment.Name and "." in attachment.Name:
            return Path(attachment.Name).suffix

        if attachment.ContentType:
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

            extension = content_type_map.get(attachment.ContentType)
            if extension:
                return extension

            guessed_extension = mimetypes.guess_extension(attachment.ContentType)
            if guessed_extension:
                return guessed_extension

        logger.warning(
            f"Could not determine file extension for attachment: {attachment.Name}"
        )
        return ""

    async def save_recipients(
        self, email_data: PostmarkWebhookRequest, email_id: int
    ) -> List[EmailRecipient]:
        """Save email recipients to database."""
        recipients = []

        if email_data.FromFull:
            from_recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientType.FROM,
                email_address=email_data.FromFull.Email,
                name=email_data.FromFull.Name,
                mailbox_hash=email_data.FromFull.MailboxHash,
            )
            recipients.append(from_recipient)

        for to_recipient in email_data.ToFull or []:
            recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientType.TO,
                email_address=to_recipient.Email,
                name=to_recipient.Name,
                mailbox_hash=to_recipient.MailboxHash,
            )
            recipients.append(recipient)

        for cc_recipient in email_data.CcFull or []:
            recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientType.CC,
                email_address=cc_recipient.Email,
                name=cc_recipient.Name,
                mailbox_hash=cc_recipient.MailboxHash,
            )
            recipients.append(recipient)

        for bcc_recipient in email_data.BccFull or []:
            recipient = EmailRecipient(
                email_id=email_id,
                recipient_type=RecipientType.BCC,
                email_address=bcc_recipient.Email,
                name=bcc_recipient.Name,
                mailbox_hash=bcc_recipient.MailboxHash,
            )
            recipients.append(recipient)

        for recipient in recipients:
            self.db.add(recipient)

        return recipients

    async def save_headers(
        self, headers: List[EmailHeaderData], email_id: int
    ) -> List[EmailHeader]:
        """Save email headers to the database."""
        db_headers = [
            EmailHeader(
                email_id=email_id,
                name=header.Name,
                value=header.Value,
            )
            for header in headers
        ]
        self.db.add_all(db_headers)
        return db_headers

    async def process_webhook_email(
        self, raw_email: RawEmail, email_data: PostmarkWebhookRequest, user_id: int
    ) -> Email:
        """Process the validated webhook data and save it as a structured email."""
        logger.info(
            f"Processing webhook email for user {user_id}, message_id: {email_data.MessageID}"
        )

        email_identifier = self.extract_email_identifier(email_data.Headers)
        parent_identifier = self.extract_parent_email_identifier(email_data.Headers)
        parent_email_id = await self.get_parent_email_id(parent_identifier)
        spam_score, spam_status = self.parse_spam_status(email_data.Headers)

        existing_email = await self.check_duplicate_email(
            email_data.MessageID, email_identifier
        )
        if existing_email:
            logger.warning(
                f"Duplicate email detected. MessageID: {email_data.MessageID}, Identifier: {email_identifier}"
            )
            return existing_email

        sent_at = self.parse_date(email_data.Date)

        new_email = Email(
            raw_email_id=raw_email.id,
            user_id=user_id,
            message_id=email_data.MessageID,
            message_stream=email_data.MessageStream,
            from_email=email_data.FromFull.Email,
            from_name=email_data.FromFull.Name,
            subject=email_data.Subject,
            text_body=email_data.TextBody,
            html_body=email_data.HtmlBody,
            stripped_text_reply=email_data.StrippedTextReply,
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

        self.db.add(new_email)
        await self.db.flush()

        recipients = await self.save_recipients(email_data, new_email.id)

        await self._assign_email_to_thread(new_email, email_data, recipients)

        await self.save_attachments(email_data.Attachments or [], new_email.id)
        await self.save_headers(email_data.Headers, new_email.id)

        raw_email.processing_status = ProcessingStatus.PROCESSED

        await self.db.commit()
        await self.db.refresh(new_email)
        logger.info(f"Successfully processed email {new_email.id} for user {user_id}")
        return new_email

    async def _assign_email_to_thread(
        self,
        email: Email,
        email_data: PostmarkWebhookRequest,
        recipients: List[EmailRecipient],
    ) -> None:
        """Assign email to a thread (create new or use existing)."""
        try:
            participants = []

            participants.append(email_data.From)

            for recipient in recipients:
                if recipient.recipient_type in [RecipientType.TO, RecipientType.CC]:
                    participants.append(recipient.email_address)

            participants = sorted(list(set(participants)))

            thread_summary = self._generate_thread_summary(email_data)

            thread = await self.thread_service.create_or_get_thread(
                subject=email_data.Subject or "",
                participants=participants,
                thread_summary=thread_summary,
            )

            await self.thread_service.add_email_to_thread(email, thread)

        except Exception as e:
            logger.error(f"Failed to assign email to thread: {str(e)}")

            pass

    def _generate_thread_summary(self, email_data: PostmarkWebhookRequest) -> str:
        """Generate a summary for the email thread."""
        subject = email_data.Subject or "No subject"
        sender = email_data.FromName or email_data.From

        summary = f"Email thread: {subject}"

        if email_data.TextBody:
            text_preview = email_data.TextBody.strip()[:200]
            if len(text_preview) == 200:
                text_preview += "..."
            summary += f"\n\nPreview: {text_preview}"
        elif email_data.StrippedTextReply:
            text_preview = email_data.StrippedTextReply.strip()[:200]
            if len(text_preview) == 200:
                text_preview += "..."
            summary += f"\n\nPreview: {text_preview}"

        summary += f"\n\nStarted by: {sender}"

        if email_data.Attachments:
            summary += f"\n\nAttachments: {len(email_data.Attachments)} file(s)"

        return summary

    def _trigger_actionables_processing(self, email_id: int) -> None:
        """
        Trigger actionables processing in the background without blocking the webhook response.
        This method creates a detached task that processes actionables asynchronously.
        """
        try:
            from app.modules.actionables.actionables import (
                get_email_thread_content,
                process_actionables_detached,
            )

            async def process_actionables_wrapper():
                try:
                    email_thread_content = await get_email_thread_content(email_id)

                    await process_actionables_detached(email_id, email_thread_content)

                except Exception as e:
                    logger.error(
                        f"Error in actionables processing wrapper for email {email_id}: {str(e)}",
                        exc_info=e,
                    )

            asyncio.create_task(process_actionables_wrapper())
            logger.info(
                f"Triggered background actionables processing for email_id: {email_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to trigger actionables processing for email {email_id}: {str(e)}"
            )

    async def process_postmark_webhook(self, raw_data: Dict) -> Dict[str, str]:
        """High-level function to process an incoming Postmark webhook."""
        logger.info("Processing incoming Postmark webhook")
        raw_email = None
        try:
            email_data = self.validate_webhook_request(raw_data)
            user_service = get_user_webhook_service()
            user, _ = await user_service.process_user_from_webhook(
                email=email_data.OriginalRecipient,
                mailbox_hash=email_data.MailboxHash,
            )

            if not user:
                raise Exception("User could not be created or retrieved.")

            raw_email = await self.save_raw_email(raw_data)

            processed_email = await self.process_webhook_email(
                raw_email, email_data, user.id
            )

            await self.db.commit()

            attachments_count = len(email_data.Attachments or [])

            self._trigger_actionables_processing(processed_email.id)

            return {
                "email_id": str(processed_email.id),
                "raw_email_id": str(raw_email.id),
                "message_id": processed_email.message_id,
                "attachments_count": str(attachments_count),
                "duplicate": "false",
            }
        except Exception as e:
            logger.error(f"Error processing Postmark webhook: {str(e)}")
            if raw_email:
                raw_email.processing_status = ProcessingStatus.FAILED
                raw_email.error_message = str(e)
                await self.db.commit()
            raise


async def get_webhook_service(db_session: AsyncSession) -> WebhookProcessingService:
    """Factory function to create webhook processing service."""
    return WebhookProcessingService(db_session)
