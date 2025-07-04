from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.core.dependencies import get_current_user
from app.core.utils.response.response import PaginatedResponse
from app.modules.actionables.api import (
    ActionableListRequest,
    GroupedActionablesResponse,
)
from app.modules.actionables.services import ActionableService, get_actionable_service
from app.modules.users import User

router = APIRouter(prefix="/actionables", tags=["actionables"])


@router.post("/list", response_model=PaginatedResponse[GroupedActionablesResponse])
async def list_actionables(
    request: ActionableListRequest,
    actionable_service: ActionableService = Depends(get_actionable_service),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    List all actionables for the current user with filtering and pagination, grouped by type.
    """
    try:
        grouped_actionables, total_count = await actionable_service.list_actionables(
            request, user.id
        )

        return PaginatedResponse.success(
            message="Actionables retrieved successfully",
            data=[grouped_actionables.model_dump(mode="json")],
            page=request.page,
            limit=request.limit,
            total_items=total_count,
        )

    except Exception as e:
        return PaginatedResponse.failure(
            message=str(e),
            page=request.page,
            limit=request.limit,
            total_items=0,
            http_status_code=500,
        )
