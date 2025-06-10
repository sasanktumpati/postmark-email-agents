import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_config
from app.core.db.database import get_db_session
from app.core.logger import get_logger, log_api_access, log_auth_event
from app.modules.users.repository import user_repository
from app.modules.users.services import verify_api_key

logger = get_logger("middleware.auth")
API_KEY_HEADER = "X-API-Key"


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        logger.debug(
            f"RateLimiter initialized with max_requests={max_requests}, window_seconds={window_seconds}"
        )

    def is_allowed(self, api_key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        self.requests[api_key] = [
            req_time for req_time in self.requests[api_key] if req_time > window_start
        ]
        logger.debug(f"Checking rate limit for API key: {api_key[:8]}...")

        if len(self.requests[api_key]) >= self.max_requests:
            logger.debug(f"Rate limit exceeded for API key: {api_key[:8]}...")
            return False

        self.requests[api_key].append(now)
        logger.debug(
            f"API key {api_key[:8]}... is allowed. Request count: {len(self.requests[api_key])}"
        )
        return True

    def get_retry_after(self, api_key: str) -> int:
        if not self.requests[api_key]:
            return 0
        oldest_request = min(self.requests[api_key])
        retry_time = int(self.window_seconds - (time.time() - oldest_request))
        logger.debug(
            f"Calculating retry-after for API key {api_key[:8]}...: {retry_time}s"
        )
        return retry_time


rate_limiter = None


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_prefixes: Optional[list] = None):
        super().__init__(app)
        self.excluded_prefixes = excluded_prefixes or [
            "/v1/health",
            "/docs",
            "/openapi.json",
            "/v1/postmark-webhook",
        ]
        logger.debug(
            f"AuthMiddleware initialized. Excluded prefixes: {self.excluded_prefixes}"
        )

        global rate_limiter
        if rate_limiter is None:
            settings = get_config()
            rate_limiter = RateLimiter(
                max_requests=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
            logger.info("Rate limiter initialized from application settings.")

    async def dispatch(self, request: Request, call_next):
        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host
        elif "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            client_ip = request.headers["x-real-ip"]
        logger.debug(
            f"Dispatching request: {request.method} {request.url.path} from IP: {client_ip}"
        )

        if request.method == "OPTIONS":
            logger.debug("Skipping authentication for OPTIONS request.")
            return await call_next(request)

        if any(
            request.url.path.startswith(prefix) for prefix in self.excluded_prefixes
        ):
            logger.debug(
                f"Skipping authentication for excluded path: {request.url.path}"
            )
            return await call_next(request)

        api_key = request.headers.get(API_KEY_HEADER)
        api_key_truncated = (
            api_key[:8] + "..." if api_key and len(api_key) > 8 else "NONE"
        )
        logger.debug(f"Extracted API key (truncated): {api_key_truncated}")

        if not api_key:
            logger.warning(
                f"Missing API key for request: {request.method} {request.url.path} "
                f"from {client_ip}"
            )
            log_auth_event(
                "MISSING_API_KEY",
                client_ip,
                "NONE",
                None,
                f"{request.method} {request.url.path}",
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "API Key is missing",
                    "error_code": "MISSING_API_KEY",
                    "hint": f"Include your API key in the '{API_KEY_HEADER}' header",
                },
            )

        if not rate_limiter.is_allowed(api_key):
            retry_after = rate_limiter.get_retry_after(api_key)
            logger.warning(
                f"Rate limit exceeded for API key (truncated): {api_key_truncated} "
                f"from {client_ip}"
            )
            log_auth_event(
                "RATE_LIMIT_EXCEEDED",
                client_ip,
                api_key_truncated,
                None,
                f"{request.method} {request.url.path} | Retry after: {retry_after}s",
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        user_id = verify_api_key(api_key)
        if not user_id:
            logger.warning(
                f"Invalid API key signature for request: {request.method} {request.url.path} "
                f"from {client_ip} "
                f"API key (truncated): {api_key_truncated}"
            )
            log_auth_event(
                "INVALID_API_KEY_SIGNATURE",
                client_ip,
                api_key_truncated,
                None,
                f"{request.method} {request.url.path}",
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Invalid API Key",
                    "error_code": "INVALID_API_KEY",
                    "hint": "Please check your API key and try again",
                },
            )
        logger.debug(f"API key valid. User ID: {user_id}")

        async with get_db_session() as session:
            try:
                user = await user_repository.get(session, user_id)
                logger.debug(f"User {user_id} fetched from database.")
            except Exception as e:
                logger.error(
                    f"Database error during user lookup for user_id {user_id}: {e}"
                )
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "detail": "Internal server error",
                        "error_code": "DATABASE_ERROR",
                    },
                )

        if not user:
            logger.warning(
                f"User not found for valid API key: user_id={user_id}, "
                f"API key (truncated): {api_key_truncated}"
            )
            log_auth_event(
                "USER_NOT_FOUND",
                client_ip,
                api_key_truncated,
                str(user_id),
                f"{request.method} {request.url.path}",
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "User not found", "error_code": "USER_NOT_FOUND"},
            )
        logger.debug(f"User {user.email} found. Checking account status.")

        if not user.is_active:
            logger.warning(
                f"Inactive user attempted access: user_id={user_id}, email={user.email}"
            )
            log_auth_event(
                "USER_INACTIVE",
                client_ip,
                api_key_truncated,
                str(user_id),
                f"{request.method} {request.url.path} | Email: {user.email}",
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "User account is inactive",
                    "error_code": "USER_INACTIVE",
                },
            )
        logger.debug(f"User {user.email} is active.")

        if user.api_key != api_key:
            logger.warning(
                f"API key mismatch for user {user_id}: stored key doesn't match provided key"
            )
            log_auth_event(
                "API_KEY_MISMATCH",
                client_ip,
                api_key_truncated,
                str(user_id),
                f"{request.method} {request.url.path} | Email: {user.email}",
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "API key mismatch",
                    "error_code": "API_KEY_MISMATCH",
                },
            )
        logger.debug(f"API key matches for user {user.email}.")

        now = datetime.utcnow()

        if user.first_login_at is None:
            user.first_login_at = now
            logger.info(f"First login recorded for user {user_id} ({user.email})")

        user.last_successful_auth_at = now
        logger.debug(f"Last successful authentication recorded for user {user.email}.")

        if user.failed_auth_attempts > 0:
            user.failed_auth_attempts = 0
            user.last_failed_auth_at = None
            user.account_locked_until = None
            logger.info(
                f"Reset failed auth attempts for user {user_id} after successful login"
            )

        try:
            await user_repository.update(session, user)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to update user login timestamps: {e}")

            await session.rollback()

        logger.info(
            f"Successful authentication: user_id={user_id}, email={user.email}, "
            f"endpoint={request.method} {request.url.path}"
        )

        log_api_access(
            client_ip,
            str(user_id),
            api_key_truncated,
            request.method,
            request.url.path,
            "SUCCESS",
        )

        log_auth_event(
            "LOGIN_SUCCESS",
            client_ip,
            api_key_truncated,
            str(user_id),
            f"{request.method} {request.url.path} | Email: {user.email} | First login: {user.first_login_at is None}",
        )

        request.state.user = user
        request.state.api_key = api_key
        request.state.client_ip = client_ip

        return await call_next(request)
