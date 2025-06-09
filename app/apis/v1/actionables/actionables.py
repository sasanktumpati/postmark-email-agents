from fastapi import APIRouter, Depends, HTTPException

from app.core.utils.response.response import PaginatedResponse
from app.modules.actionables.api import ActionableListRequest, ActionableObject
from app.modules.actionables.services import ActionableService, get_actionable_service

router = APIRouter(prefix="/actionables", tags=["actionables"])


@router.post("/list", response_model=PaginatedResponse[ActionableObject])
async def list_actionables(
    request: ActionableListRequest,
    actionable_service: ActionableService = Depends(get_actionable_service),
):
    """
    List all actionables with filtering and pagination.
    """
    try:
        actionables, total_count = await actionable_service.list_actionables(request)
        return PaginatedResponse.success(
            message="Actionables retrieved successfully",
            data=actionables,
            page=request.page,
            limit=request.limit,
            total_items=total_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
