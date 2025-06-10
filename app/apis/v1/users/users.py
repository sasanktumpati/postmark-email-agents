from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, ValidationError

from app.core.dependencies import get_current_user
from app.core.logger import get_logger
from app.core.utils.response.response import BaseResponse
from app.modules.users.db import User

logger = get_logger(__name__)

router = APIRouter(prefix="/users")
logger.info("Initializing users router.")


class UserProfileResponse(BaseModel):
    """Response model for user profile"""

    name: Optional[str] = None
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/me", summary="Get current user profile")
async def get_me(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Retrieve the current authenticated user's profile details.
    """
    try:
        logger.info(f"User {current_user.email} requested their profile details.")

        user_profile = UserProfileResponse.model_validate(current_user)

        logger.debug(f"Successfully retrieved profile for user {current_user.email}")
        return BaseResponse.success(
            message="User profile retrieved successfully",
            data=user_profile.model_dump(mode="json"),
        )

    except ValidationError as e:
        logger.error(
            f"Validation error for user {current_user.email if current_user else 'unknown'}: {e}"
        )
        return BaseResponse.failure(
            message="Failed to validate user profile data",
            http_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    except AttributeError as e:
        logger.error(
            f"Missing user attributes for user {current_user.email if current_user else 'unknown'}: {e}"
        )
        return BaseResponse.failure(
            message="User profile data is incomplete",
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    except Exception as e:
        logger.error(
            f"Unexpected error retrieving profile for user {current_user.email if current_user else 'unknown'}: {e}"
        )
        return BaseResponse.failure(
            message="An unexpected error occurred while retrieving user profile",
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
