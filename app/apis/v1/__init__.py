from fastapi import APIRouter

from app.core.logger import get_logger

from .actionables import router as actionables_router
from .emails import router as emails_router
from .health import health
from .users import router as users_router
from .webhook import router as webhook_router

logger = get_logger(__name__)

router = APIRouter(prefix="/v1")
logger.info("Initializing API router for /v1 prefix.")

router.include_router(webhook_router, tags=["webhook"])
logger.info("Webhook router included.")

router.include_router(health.router, tags=["health"])
logger.info("Health router included.")

router.include_router(emails_router, tags=["emails"])
logger.info("Emails router included.")

router.include_router(actionables_router, tags=["actionables"])
logger.info("Actionables router included.")

router.include_router(users_router, tags=["users"])
logger.info("Users router included.")
