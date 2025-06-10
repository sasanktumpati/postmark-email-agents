from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.repository import Repository
from app.core.logger import get_logger
from app.modules.users.db import EmailSendStatus, SentEmail, User
from app.modules.users.models.response import PostmarkEmailResponse

logger = get_logger(__name__)


class UserRepository(Repository[User]):
    """Repository for User operations."""

    def __init__(self):
        super().__init__(User)
        logger.debug("UserRepository initialized.")

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address."""
        logger.debug(f"Attempting to retrieve user by email: {email}")
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"User found by email: {email}")
        else:
            logger.debug(f"User not found by email: {email}")
        return user

    async def get_by_mailbox_hash(
        self, session: AsyncSession, mailbox_hash: str
    ) -> Optional[User]:
        """Get user by mailbox hash."""
        logger.debug(f"Attempting to retrieve user by mailbox hash: {mailbox_hash}")
        query = select(User).where(User.mailbox_hash == mailbox_hash)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"User found by mailbox hash: {mailbox_hash}")
        else:
            logger.debug(f"User not found by mailbox hash: {mailbox_hash}")
        return user

    async def create_user(
        self, session: AsyncSession, email: str, mailbox_hash: str, name: str
    ) -> User:
        """Create a new user."""
        logger.debug(f"Creating new user with email: {email}")
        user = User(
            email=email,
            name=name,
            mailbox_hash=mailbox_hash,
        )
        new_user = await self.create(session, user)
        logger.info(f"User created successfully: {new_user.email}")
        return new_user

    async def get_or_create_user(
        self, session: AsyncSession, email: str, mailbox_hash: str, name: str
    ) -> Tuple[User, bool]:
        """Get existing user or create new one. Returns (user, created)."""
        logger.debug(f"Attempting to get or create user for email: {email}")
        user = await self.get_by_email(session, email)

        if user:
            logger.debug(f"User found for email: {email}. Checking for updates.")
            if user.mailbox_hash != mailbox_hash or user.name != name:
                logger.debug(f"Updating mailbox hash or name for user: {email}")
                user.mailbox_hash = mailbox_hash
                user.name = name
                updated_user = await self.update(session, user)
                logger.info(f"User {email} updated successfully.")
                return updated_user, False
            logger.debug(f"No updates needed for user: {email}")
            return user, False

        user = await self.create_user(session, email, mailbox_hash, name)
        logger.info(f"User {email} created during get_or_create.")
        return user, True


class SentEmailRepository(Repository[SentEmail]):
    """Repository for SentEmail operations."""

    def __init__(self):
        super().__init__(SentEmail)
        logger.debug("SentEmailRepository initialized.")

    async def log_email_attempt(
        self,
        session: AsyncSession,
        user_id: int,
        from_email: str,
        to_email: str,
        api_key: str,
        response: Dict[str, Any],
        is_silent_failure: bool = False,
    ) -> SentEmail:
        """Log an email sending attempt with proper error tracking."""
        logger.debug(f"Logging email attempt for user_id: {user_id}, to: {to_email}")
        try:
            postmark_response = PostmarkEmailResponse(**response)
            logger.debug(
                f"Successfully parsed Postmark response for email to {to_email}."
            )
        except Exception as e:
            logger.warning(
                f"Failed to parse Postmark response for email to {to_email}: {e}. Using fallback parsing."
            )

            postmark_response = PostmarkEmailResponse(
                error_code=response.get("ErrorCode", 0),
                message=response.get("Message"),
                message_id=response.get("MessageID"),
                submitted_at=response.get("SubmittedAt"),
            )

        status = (
            EmailSendStatus.SENT
            if postmark_response.error_code == 0
            else EmailSendStatus.FAILED
        )
        logger.debug(f"Email send status for {to_email}: {status.value}")

        sent_email = SentEmail(
            user_id=user_id,
            from_email=from_email,
            to_email=to_email,
            api_key=api_key,
            status=status,
            error_code=postmark_response.error_code,
            message=postmark_response.message,
            message_id=postmark_response.message_id,
            submitted_at=postmark_response.submitted_at,
            postmark_error_code=postmark_response.error_code,
            failure_reason=postmark_response.message
            if status == EmailSendStatus.FAILED
            else None,
            is_silent_failure=is_silent_failure,
            retry_count=0,
        )

        logged_email = await self.create(session, sent_email)
        logger.info(
            f"Email attempt logged for user {user_id} to {to_email} with status {status.value}."
        )
        return logged_email

    async def update_retry_attempt(
        self, session: AsyncSession, sent_email: SentEmail, error_message: str
    ) -> SentEmail:
        """Update retry information for a failed email."""
        logger.debug(
            f"Updating retry attempt for email ID: {sent_email.id}, current retry count: {sent_email.retry_count}"
        )
        sent_email.retry_count += 1
        sent_email.last_retry_at = datetime.utcnow()
        sent_email.failure_reason = error_message
        sent_email.status = EmailSendStatus.RETRYING

        updated_email = await self.update(session, sent_email)
        logger.info(
            f"Email ID {sent_email.id} updated for retry. New status: {sent_email.status.value}, retry count: {sent_email.retry_count}"
        )
        return updated_email


user_repository = UserRepository()
sent_email_repository = SentEmailRepository()
