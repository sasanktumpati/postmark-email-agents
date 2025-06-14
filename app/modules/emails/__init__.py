from app.core.logger import get_logger

from .get_emails import EmailRetrievalService, get_email_service
from .models import *
from .process_webhook import WebhookProcessingService, get_webhook_service
from .thread_service import EmailThreadService, get_thread_service

logger = get_logger(__name__)
logger.info("Initializing emails module.")

__all__ = [
    "EmailRetrievalService",
    "EmailThreadService",
    "WebhookProcessingService",
    "get_email_service",
    "get_thread_service",
    "get_webhook_service",
]
