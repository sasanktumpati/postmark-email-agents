import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db
from app.core.utils.response import BaseResponse, ErrorDetails
from app.modules.emails import (
    WebhookProcessingResponse,
    get_webhook_service,
)

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """Model for health check result data."""

    def __init__(self, service: str, health_status: str, timestamp: str, version: str):
        self.service = service
        self.health_status = health_status
        self.timestamp = timestamp
        self.version = version


router: APIRouter = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post(
    "/postmark-webhook",
    response_model=BaseResponse[WebhookProcessingResponse],
)
async def postmark_webhook(
    request: Request, db: AsyncSession = Depends(get_async_db)
) -> JSONResponse:
    """Process Postmark inbound email webhook."""
    start_time = time.time()

    try:
        raw_data = await request.json()

        logger.info(
            f"Received Postmark webhook with MessageID: {raw_data.get('MessageID', 'unknown')}"
        )

        # Get webhook processing service
        webhook_service = await get_webhook_service(db)

        # Process the webhook
        result = await webhook_service.process_postmark_webhook(raw_data)

        processing_time = (time.time() - start_time) * 1000

        # Create response using new model
        response_data = WebhookProcessingResponse(
            email_id=result["email_id"],
            raw_email_id=result["raw_email_id"],
            message_id=result["message_id"],
            processing_status="processed",
            is_duplicate=result.get("duplicate", "false") == "true",
            processing_time_ms=processing_time,
            attachments_count=int(result.get("attachments_count", 0)),
        )

        response = BaseResponse.success(
            message="Email processed successfully",
            data=response_data,
            status_code=201 if not response_data.is_duplicate else 200,
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


@router.get("/health")
async def webhook_health() -> BaseResponse[dict]:
    """Health check endpoint for the webhook service."""
    from datetime import datetime

    health_data = {
        "service": "postmark-webhook",
        "health_status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }

    return BaseResponse.success(
        message="Webhook service is healthy",
        data=health_data,
    )
