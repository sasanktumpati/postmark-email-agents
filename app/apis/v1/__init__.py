from fastapi import APIRouter

from .health import health
from .webhook import router as webhook_router

router = APIRouter(prefix="/v1")
router.include_router(webhook_router, tags=["webhook"])
router.include_router(health.router, tags=["health"])
