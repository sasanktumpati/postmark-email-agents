import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.repository import Repository
from app.modules.users.db import EmailSendStatus, SentEmail, User
from app.modules.users.models.response import PostmarkEmailResponse

logger = logging.getLogger(__name__)


class UserRepository(Repository[User]):
    """Repository for User operations."""

    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address."""
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_mailbox_hash(
        self, session: AsyncSession, mailbox_hash: str
    ) -> Optional[User]:
        """Get user by mailbox hash."""
        query = select(User).where(User.mailbox_hash == mailbox_hash)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_user(
        self, session: AsyncSession, email: str, mailbox_hash: str
    ) -> User:
        """Create a new user with email and mailbox_hash as name."""
        user = User(
            email=email,
            name=mailbox_hash,
            mailbox_hash=mailbox_hash,
        )
        return await self.create(session, user)

    async def get_or_create_user(
        self, session: AsyncSession, email: str, mailbox_hash: str
    ) -> Tuple[User, bool]:
        """Get existing user or create new one. Returns (user, created)."""

        user = await self.get_by_email(session, email)

        if user:
            if user.mailbox_hash != mailbox_hash:
                user.mailbox_hash = mailbox_hash
                user.name = mailbox_hash
                await self.update(session, user)
            return user, False

        user = await self.create_user(session, email, mailbox_hash)
        return user, True


class SentEmailRepository(Repository[SentEmail]):
    """Repository for SentEmail operations."""

    def __init__(self):
        super().__init__(SentEmail)

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

        try:
            postmark_response = PostmarkEmailResponse(**response)
        except Exception as e:
            logger.warning(
                f"Failed to parse Postmark response: {e}. Using fallback parsing."
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

        return await self.create(session, sent_email)

    async def update_retry_attempt(
        self, session: AsyncSession, sent_email: SentEmail, error_message: str
    ) -> SentEmail:
        """Update retry information for a failed email."""
        sent_email.retry_count += 1
        sent_email.last_retry_at = datetime.utcnow()
        sent_email.failure_reason = error_message
        sent_email.status = EmailSendStatus.RETRYING

        return await self.update(session, sent_email)


user_repository = UserRepository()
sent_email_repository = SentEmailRepository()
