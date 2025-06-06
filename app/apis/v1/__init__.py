from fastapi import APIRouter

from .emails import router as emails_router
from .health import health
from .webhook import router as webhook_router

router = APIRouter(prefix="/v1")
router.include_router(webhook_router, tags=["webhook"])
router.include_router(health.router, tags=["health"])
router.include_router(emails_router, tags=["emails"])
