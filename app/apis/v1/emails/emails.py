from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db
from app.core.db.database import get_db_session
from app.core.dependencies import get_current_user
from app.core.logger import get_logger
from app.core.utils.response.response import (
    BaseResponse,
    ErrorDetails,
    PaginatedResponse,
)
from app.modules.emails import (
    EmailAttachmentResponse,
    EmailDetailResponse,
    EmailHeaderResponse,
    EmailListItemResponse,
    EmailListRequest,
    EmailRecipientResponse,
    EmailStatsResponse,
    get_email_service,
)
from app.modules.users import User

logger = get_logger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"])


def _convert_email_to_list_response(
    email, attachment_count=0, recipient_count=0
) -> EmailListItemResponse:
    """Convert Email model to EmailListItemResponse."""
    return EmailListItemResponse(
        id=email.id,
        message_id=email.message_id,
        message_stream=email.message_stream,
        from_email=email.from_email,
        from_name=email.from_name,
        subject=email.subject,
        sent_at=email.sent_at,
        processed_at=email.processed_at,
        mailbox_hash=email.mailbox_hash,
        tag=email.tag,
        original_recipient=email.original_recipient,
        reply_to=email.reply_to,
        spam_score=email.spam_score,
        spam_status=email.spam_status.value
        if hasattr(email.spam_status, "value")
        else str(email.spam_status),
        stripped_text_body=email.stripped_text_reply,
        has_attachments=attachment_count > 0,
        attachment_count=attachment_count,
        recipient_count=recipient_count,
    )


def _convert_email_to_detail_response(email) -> EmailDetailResponse:
    """Converts Email model to EmailDetailResponse."""

    recipients = [
        EmailRecipientResponse(
            id=r.id,
            recipient_type=r.recipient_type.value
            if hasattr(r.recipient_type, "value")
            else str(r.recipient_type),
            email_address=r.email_address,
            name=r.name,
            mailbox_hash=r.mailbox_hash,
        )
        for r in email.recipients
    ]

    attachments = [
        EmailAttachmentResponse(
            id=a.id,
            filename=a.filename,
            content_type=a.content_type,
            content_length=a.content_length,
            content_id=a.content_id,
            file_url=a.file_url,
            created_at=a.created_at,
        )
        for a in email.attachments
    ]

    headers = [
        EmailHeaderResponse(
            id=h.id,
            name=h.name,
            value=h.value,
        )
        for h in email.headers
    ]

    return EmailDetailResponse(
        id=email.id,
        raw_email_id=email.raw_email_id,
        message_id=email.message_id,
        message_stream=email.message_stream,
        from_email=email.from_email,
        from_name=email.from_name,
        subject=email.subject,
        text_body=email.text_body,
        html_body=email.html_body,
        stripped_text_body=email.stripped_text_reply,
        sent_at=email.sent_at,
        processed_at=email.processed_at,
        mailbox_hash=email.mailbox_hash,
        tag=email.tag,
        original_recipient=email.original_recipient,
        reply_to=email.reply_to,
        parent_email_id=email.parent_email_id,
        parent_email_identifier=email.parent_email_identifier,
        email_identifier=email.email_identifier,
        spam_score=email.spam_score,
        spam_status=email.spam_status.value
        if hasattr(email.spam_status, "value")
        else str(email.spam_status),
        recipients=recipients,
        attachments=attachments,
        headers=headers,
    )


@router.post("/list", response_model=PaginatedResponse[EmailListItemResponse])
async def list_emails(
    request: EmailListRequest,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    List emails with pagination, search, and sorting for the current user.

    - **page**: Page number (1-based)
    - **limit**: Number of items per page (1-100)
    - **search**: Optional search parameters
    - **sort_by**: Field to sort by (sent_at, processed_at, from_email, subject, spam_score, message_id)
    - **sort_order**: Sort order (asc, desc)
    """
    try:
        email_service = await get_email_service(db)

        emails, total_count = await email_service.get_emails_with_pagination(
            user_id=user.id,
            page=request.page,
            limit=request.limit,
            search_params=request.search,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )

        email_responses = []
        for email in emails:
            attachment_count = len(email.attachments) if email.attachments else 0
            recipient_count = len(email.recipients) if email.recipients else 0

            email_response = _convert_email_to_list_response(
                email, attachment_count, recipient_count
            )
            email_responses.append(email_response)

        return PaginatedResponse.success(
            message="Emails retrieved successfully",
            data=[response.model_dump(mode="json") for response in email_responses],
            page=request.page,
            limit=request.limit,
            total_items=total_count,
        )

    except ValueError as e:
        return PaginatedResponse.failure(
            message="Invalid request parameters",
            http_status_code=400,
            page=request.page,
            limit=request.limit,
            data=ErrorDetails(
                error_code="INVALID_PARAMETERS",
                error_type="ValidationError",
                details={"validation_error": str(e)},
                suggestions="Please check your request parameters",
            ),
        )
    except Exception as e:
        return PaginatedResponse.failure(
            message="Failed to retrieve emails",
            http_status_code=500,
            page=request.page,
            limit=request.limit,
            data=ErrorDetails(
                error_code="INTERNAL_SERVER_ERROR",
                error_type="RetrievalError",
                details={"error": str(e)},
                suggestions="Please check your request parameters and try again, or contact support if the issue persists",
            ),
        )


@router.get("/{email_id}", response_model=BaseResponse[EmailDetailResponse])
async def get_email_details(
    email_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Get detailed information about a specific email belonging to the current user.

    - **email_id**: ID of the email to retrieve
    """
    try:
        if email_id <= 0:
            return BaseResponse.failure(
                message="Invalid email ID", http_status_code=400
            )

        email_service = await get_email_service(db)
        email = await email_service.get_email_by_id(email_id, user_id=user.id)

        if not email:
            return BaseResponse.failure(
                message="Email not found",
                http_status_code=404,
                data=ErrorDetails(
                    error_code="EMAIL_NOT_FOUND",
                    error_type="NotFoundError",
                    details={"email_id": email_id},
                    suggestions="Please check the email ID and ensure you have access to this email",
                ),
            )

        email_response = _convert_email_to_detail_response(email)

        return BaseResponse.success(
            message="Email details retrieved successfully",
            data=email_response.model_dump(mode="json"),
        )

    except Exception as e:
        return BaseResponse.failure(
            message="Failed to retrieve email details",
            http_status_code=500,
            data=ErrorDetails(
                error_code="INTERNAL_SERVER_ERROR",
                error_type="RetrievalError",
                details={"error": str(e)},
                suggestions="Please check the email ID and try again, or contact support if the issue persists",
            ),
        )


@router.get(
    "/{email_id}/thread", response_model=BaseResponse[List[EmailDetailResponse]]
)
async def get_email_thread(
    email_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Get the complete email thread for a specific email belonging to the current user.
    Returns emails sorted by sent_at time.

    - **email_id**: ID of the email to get the thread for
    """
    try:
        if email_id <= 0:
            return BaseResponse.failure(
                message="Invalid email ID", http_status_code=400
            )

        email_service = await get_email_service(db)
        thread_emails = await email_service.get_email_thread(email_id, user_id=user.id)

        if not thread_emails:
            return BaseResponse.failure(
                message="Email thread not found",
                http_status_code=404,
                data=ErrorDetails(
                    error_code="THREAD_NOT_FOUND",
                    error_type="NotFoundError",
                    details={"email_id": email_id},
                    suggestions="Please check the email ID and ensure you have access to this email",
                ),
            )

        thread_emails.sort(key=lambda email: email.sent_at or email.processed_at)

        email_responses = []
        for email in thread_emails:
            email_response = _convert_email_to_detail_response(email)
            email_responses.append(email_response)

        return BaseResponse.success(
            message=f"Email thread retrieved successfully with {len(email_responses)} emails",
            data=[response.model_dump(mode="json") for response in email_responses],
        )

    except Exception as e:
        return BaseResponse.failure(
            message="Failed to retrieve email thread",
            http_status_code=500,
            data=ErrorDetails(
                error_code="INTERNAL_SERVER_ERROR",
                error_type="RetrievalError",
                details={"error": str(e)},
                suggestions="Please check the email ID and try again, or contact support if the issue persists",
            ),
        )


@router.get("/stats/summary", response_model=BaseResponse[EmailStatsResponse])
async def get_email_stats(
    db: AsyncSession = Depends(get_async_db), user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Get email statistics summary for the current user.

    Returns counts of total emails, spam emails, non-spam emails, and unique senders.
    """
    try:
        email_service = await get_email_service(db)
        stats = await email_service.get_email_stats(user_id=user.id)

        stats_response = EmailStatsResponse(
            total_emails=stats["total_emails"],
            spam_emails=stats["spam_emails"],
            non_spam_emails=stats["non_spam_emails"],
            unique_senders=stats["unique_senders"],
        )

        return BaseResponse.success(
            message="Email statistics retrieved successfully",
            data=stats_response.model_dump(mode="json"),
        )

    except Exception as e:
        return BaseResponse.failure(
            message="Failed to retrieve email statistics",
            http_status_code=500,
            data=ErrorDetails(
                error_code="INTERNAL_SERVER_ERROR",
                error_type="RetrievalError",
                details={"error": str(e)},
                suggestions="Please try again or contact support if the issue persists",
            ),
        )


@router.get("/recent/{limit}", response_model=BaseResponse[List[EmailListItemResponse]])
async def get_recent_emails(
    limit: int = 10,
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Get recent emails for the current user.

    - **limit**: Maximum number of emails to return (1-50, default: 10)
    """
    try:
        if limit <= 0 or limit > 50:
            return BaseResponse.failure(
                message="Limit must be between 1 and 50", http_status_code=400
            )

        async with get_db_session() as db:
            email_service = await get_email_service(db)
            emails = await email_service.get_recent_emails(user_id=user.id, limit=limit)

            email_responses = []
            for email in emails:
                attachment_count = len(email.attachments) if email.attachments else 0
                recipient_count = len(email.recipients) if email.recipients else 0

                email_response = _convert_email_to_list_response(
                    email, attachment_count, recipient_count
                )
                email_responses.append(email_response)

        return BaseResponse.success(
            message=f"Retrieved {len(email_responses)} recent emails",
            data=[response.model_dump(mode="json") for response in email_responses],
        )

    except Exception as e:
        logger.error(f"Recent emails endpoint error: {e}", exc_info=True)
        return BaseResponse.failure(
            message="Failed to retrieve recent emails",
            http_status_code=500,
            data=ErrorDetails(
                error_code="INTERNAL_SERVER_ERROR",
                error_type="RetrievalError",
                details={"error": str(e)},
                suggestions="Please try again or contact support if the issue persists",
            ),
        )
