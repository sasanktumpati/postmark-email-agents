from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader

from app.core.logger import get_logger
from app.modules.users.db import User

logger = get_logger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(request: Request) -> User:
    logger.debug("Attempting to retrieve current user from request state.")
    user = getattr(request.state, "user", None)
    if not user:
        logger.warning(
            "No user found in request state. AuthMiddleware might be missing or credentials invalid."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    logger.debug(f"Current user {user.email} retrieved from request state.")
    return user


async def get_optional_current_user(request: Request) -> Optional[User]:
    user = getattr(request.state, "user", None)
    if user:
        logger.debug(
            f"Optional current user {user.email} retrieved from request state."
        )
    else:
        logger.debug("No optional current user found in request state.")
    return user
