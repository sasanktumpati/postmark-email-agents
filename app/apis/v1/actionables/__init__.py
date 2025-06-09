from fastapi import APIRouter

from .actionables import router as actionables_router

router = APIRouter()
router.include_router(actionables_router)
