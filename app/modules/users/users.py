import logging
from typing import Tuple

from app.modules.users.db import User
from app.modules.users.send_emails import send_welcome_email_background
from app.modules.users.services import get_or_create_user_by_email_and_mailbox

logger = logging.getLogger(__name__)


class UserWebhookService:
    """Service for processing users during webhook processing."""

    def __init__(self):
        pass

    async def process_user_from_webhook(
        self, email: str, mailbox_hash: str, send_welcome: bool = True
    ) -> Tuple[User, bool]:
        """
        Process user creation/update from webhook data.

        Args:
            email: User's email address
            mailbox_hash: Postmark mailbox hash (used as user name)
            send_welcome: Whether to send welcome email to new users

        Returns:
            Tuple[User, bool]: (user, created) where created indicates if user was newly created
        """
        try:
            if mailbox_hash is None or mailbox_hash.strip() == "":
                username = email.split("@")[0].strip()
            else:
                username = mailbox_hash.strip()

            user, created = await get_or_create_user_by_email_and_mailbox(
                email=email, mailbox_hash=mailbox_hash, name=username
            )

            if created:
                logger.info(
                    f"New user created from webhook: {user.email} (ID: {user.id})"
                )

                if send_welcome:
                    send_welcome_email_background(user, fail_silently=True)
                    logger.info(f"Welcome email scheduled for new user: {user.email}")
            else:
                logger.debug(
                    f"Existing user found from webhook: {user.email} (ID: {user.id})"
                )

            return user, created

        except Exception as e:
            logger.error(f"Error processing user from webhook: {e}")

            raise


def get_user_webhook_service() -> UserWebhookService:
    """Factory function to create user webhook service."""
    return UserWebhookService()
