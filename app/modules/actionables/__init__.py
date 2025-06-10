from app.core.logger import get_logger

from .actionables import (
    get_email_thread_content,
    process_actionables,
    process_actionables_detached,
    trigger_actionables_processing,
    update_email_actionables_status,
)
from .agents.agent_service import AgentService

logger = get_logger(__name__)
logger.info("Initializing actionables module.")

__all__ = [
    "process_actionables",
    "process_actionables_detached",
    "trigger_actionables_processing",
    "get_email_thread_content",
    "update_email_actionables_status",
    "AgentService",
]
