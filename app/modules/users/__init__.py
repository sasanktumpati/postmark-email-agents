from app.core.logger import get_logger

from .db import EmailSendStatus, SentEmail, User
from .repository import (
    SentEmailRepository,
    UserRepository,
    sent_email_repository,
    user_repository,
)
from .send_emails import (
    send_welcome_email_async,
    send_welcome_email_background,
)
from .services import (
    generate_api_key,
    get_or_create_user_by_email_and_mailbox,
    get_user_by_email,
    get_user_by_mailbox_hash,
    log_sent_email_with_silent_failure,
    verify_api_key,
)
from .users import (
    UserWebhookService,
    get_user_webhook_service,
)

logger = get_logger(__name__)
logger.info("Initializing app modules users package.")

__all__ = [
    "User",
    "SentEmail",
    "EmailSendStatus",
    "get_or_create_user_by_email_and_mailbox",
    "get_user_by_email",
    "get_user_by_mailbox_hash",
    "log_sent_email_with_silent_failure",
    "generate_api_key",
    "verify_api_key",
    "send_welcome_email_async",
    "send_welcome_email_background",
    "UserWebhookService",
    "get_user_webhook_service",
    "UserRepository",
    "SentEmailRepository",
    "user_repository",
    "sent_email_repository",
]
