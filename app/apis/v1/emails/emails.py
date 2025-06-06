from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db
from app.core.utils.response.response import (
    BaseResponse,
    ErrorDetails,
    PaginatedResponse,
)
from app.modules.emails import (
    EmailDetailResponse,
    EmailHeaderResponse,
    EmailListRequest,
    EmailListItemResponse,
    EmailRecipientResponse,
    EmailAttachmentResponse,
    EmailStatsResponse,
    EmailThreadResponse,
    get_email_service,
)

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
    request: EmailListRequest, db: AsyncSession = Depends(get_async_db)
):
    """
    List emails with pagination, search, and sorting.

    - **page**: Page number (1-based)
    - **limit**: Number of items per page (1-100)
    - **search**: Optional search parameters
    - **sort_by**: Field to sort by (sent_at, processed_at, from_email, subject, spam_score, message_id)
    - **sort_order**: Sort order (asc, desc)
    """
    try:
        email_service = await get_email_service(db)

        emails, total_count = await email_service.get_emails_with_pagination(
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
            data=email_responses,
            page=request.page,
            limit=request.limit,
            total_items=total_count,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve emails: {str(e)}"
        )


@router.get("/{email_id}", response_model=BaseResponse[EmailDetailResponse])
async def get_email_details(email_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Get detailed information about a specific email.

    - **email_id**: ID of the email to retrieve
    """
    try:
        email_service = await get_email_service(db)
        email = await email_service.get_email_by_id(email_id)

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        email_response = _convert_email_to_detail_response(email)

        return BaseResponse.success(
            message="Email details retrieved successfully", data=email_response
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve email details: {str(e)}"
        )


@router.get("/{email_id}/thread", response_model=BaseResponse[EmailThreadResponse])
async def get_email_thread(email_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Get the complete email thread for a given email.

    This endpoint returns the entire conversation thread including:
    - Parent emails (emails this email replies to)
    - Child emails (emails that reply to this email)
    - All emails in the conversation chain

    - **email_id**: ID of any email in the thread
    """
    try:
        email_service = await get_email_service(db)
        thread_emails = await email_service.get_email_thread(email_id)

        if not thread_emails:
            raise HTTPException(status_code=404, detail="Email or thread not found")

        email_responses = [
            _convert_email_to_detail_response(email) for email in thread_emails
        ]

        def calculate_depth(email_id, emails, current_depth=0):
            children = [e for e in emails if e.parent_email_id == email_id]
            if not children:
                return current_depth
            return max(
                calculate_depth(child.id, emails, current_depth + 1)
                for child in children
            )

        root_email = next(
            (e for e in thread_emails if not e.parent_email_id), thread_emails[0]
        )
        thread_depth = calculate_depth(root_email.id, thread_emails)

        thread_id = root_email.message_id

        thread_response = EmailThreadResponse(
            thread_id=thread_id,
            emails=email_responses,
            total_emails=len(email_responses),
            thread_depth=thread_depth,
        )

        return BaseResponse.success(
            message="Email thread retrieved successfully", data=thread_response
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve email thread: {str(e)}"
        )


@router.get("/stats/summary", response_model=BaseResponse[EmailStatsResponse])
async def get_email_stats(db: AsyncSession = Depends(get_async_db)):
    """
    Get email statistics and summary information.

    Returns:
    - Total number of emails
    - Non-spam emails count
    - Spam emails count
    - Unique senders count
    """
    try:
        email_service = await get_email_service(db)
        stats = await email_service.get_email_stats()

        stats_response = EmailStatsResponse(
            total_emails=stats["total_emails"],
            non_spam_emails=stats["non_spam_emails"],
            spam_emails=stats["spam_emails"],
            unique_senders=stats["unique_senders"],
        )

        return BaseResponse.success(
            message="Email statistics retrieved successfully", data=stats_response
        )

    except Exception as e:
        error_response = BaseResponse.error(
            message="Failed to retrieve email statistics",
            status_code=500,
            data=ErrorDetails(
                error_code="INTERNAL_SERVER_ERROR",
                error_type="RetrievalError",
                details={"error": str(e)},
                suggestions="Please try again or contact support if the issue persists",
            ),
        )
        raise HTTPException(
            status_code=error_response.status_code, detail=error_response.to_dict()
        )


@router.get("/recent/{limit}", response_model=BaseResponse[List[EmailListItemResponse]])
async def get_recent_emails(limit: int = 10, db: AsyncSession = Depends(get_async_db)):
    """
    Get most recent emails.

    - **limit**: Maximum number of emails to return (default: 10, max: 50)
    """
    try:
        if limit > 50:
            limit = 50

        email_service = await get_email_service(db)
        emails = await email_service.get_recent_emails(limit)

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
            data=email_responses,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve recent emails: {str(e)}"
        )
