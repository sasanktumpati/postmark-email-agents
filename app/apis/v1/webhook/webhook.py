import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db
from app.core.utils.response import BaseResponse, ErrorDetails

from .core.repo import get_email_service

logger = logging.getLogger(__name__)


class WebhookProcessingResult(BaseModel):
    """Model for webhook processing result data."""

    email_id: str = Field(..., description="Database ID of the processed email")
    raw_email_id: str = Field(..., description="ID of the raw email data stored")
    message_id: str = Field(..., description="Postmark MessageID")
    processing_status: str = Field(..., description="Processing status")
    test_mode: bool = Field(
        default=False, description="Whether this was a test request"
    )
    processing_time_ms: Optional[float] = Field(
        None, description="Time taken to process in milliseconds"
    )
    attachments_count: Optional[int] = Field(
        None, description="Number of attachments processed"
    )


class HealthCheckResult(BaseModel):
    """Model for health check result data."""

    service: str = Field(..., description="Service name")
    health_status: str = Field(..., description="Health status")
    timestamp: Optional[str] = Field(None, description="Health check timestamp")
    version: Optional[str] = Field(None, description="Service version")


router: APIRouter = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post(
    "/postmark-webhook",
    response_model=BaseResponse[WebhookProcessingResult],
)
async def postmark_webhook(
    request: Request, db: AsyncSession = Depends(get_async_db)
) -> JSONResponse:
    start_time = time.time()

    try:
        raw_data = await request.json()

        logger.info(
            f"Received Postmark webhook with MessageID: {raw_data.get('MessageID', 'unknown')}"
        )

        email_service = await get_email_service(db)

        result = await email_service.process_postmark_webhook(raw_data)

        processing_time = (time.time() - start_time) * 1000

        response = BaseResponse.success(
            message="Email processed successfully",
            data=WebhookProcessingResult(
                email_id=result["email_id"],
                raw_email_id=result["raw_email_id"],
                message_id=result["message_id"],
                processing_status="processed",
                processing_time_ms=processing_time,
                attachments_count=int(result.get("attachments_count", 0)),
            ),
            status_code=201,
        )

        return JSONResponse(
            content=response.to_dict(),
            status_code=response.status_code,
        )

    except ValueError as e:
        logger.error(f"Validation error in webhook processing: {str(e)}")
        response = BaseResponse.error(
            message="Invalid webhook data received",
            data=ErrorDetails(
                error_code="VALIDATION_ERROR",
                error_type="validation",
                details={"validation_error": str(e)},
                suggestions="Please ensure the webhook payload matches Postmark's expected format",
            ),
            status_code=422,
        )
        return JSONResponse(
            content=response.to_dict(), status_code=response.status_code
        )
    except KeyError as e:
        logger.error(f"Missing required field in webhook: {str(e)}")
        response = BaseResponse.error(
            message="Missing required field in webhook data",
            data=ErrorDetails(
                error_code="MISSING_FIELD",
                error_type="validation",
                details={"missing_field": str(e)},
                suggestions="Please check that all required fields are present in the webhook payload",
            ),
            status_code=422,
        )
        return JSONResponse(
            content=response.to_dict(), status_code=response.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}", exc_info=True)
        response = BaseResponse.error(
            message="Internal server error processing webhook",
            data=ErrorDetails(
                error_code="INTERNAL_ERROR",
                error_type="processing",
                details={"error_message": str(e)},
                suggestions="Please try again or contact support if the issue persists",
            ),
            status_code=500,
        )
        return JSONResponse(
            content=response.to_dict(),
            status_code=response.status_code,
        )


@router.get("/webhook/health", response_model=BaseResponse[HealthCheckResult])
async def webhook_health() -> BaseResponse[HealthCheckResult]:
    """Health check endpoint for the webhook service."""
    from datetime import datetime

    return BaseResponse.success(
        message="Webhook service is healthy",
        data=HealthCheckResult(
            service="postmark-webhook",
            health_status="healthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
        ),
    )
