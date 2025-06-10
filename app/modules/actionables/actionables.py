import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.sql import select, update

from app.core.db.database import get_db_transaction
from app.modules.emails.models.db import ActionablesProcessingStatus, Email

logger = logging.getLogger(__name__)


async def update_email_actionables_status(
    email_id: int,
    status: ActionablesProcessingStatus,
    error_message: Optional[str] = None,
) -> None:
    """Update the actionables processing status of an email."""
    try:
        async with get_db_transaction() as session:
            update_data = {
                "actionables_processing_status": status,
                "actionables_processed_at": datetime.now()
                if status == ActionablesProcessingStatus.PROCESSED
                else None,
            }
            if error_message:
                update_data["actionables_error_message"] = error_message

            await session.execute(
                update(Email).where(Email.id == email_id).values(**update_data)
            )
            logger.info(
                f"Updated actionables status for email {email_id} to {status.value}"
            )
    except Exception as e:
        logger.error(
            f"Failed to update actionables status for email {email_id}: {str(e)}"
        )


async def process_actionables_detached(email_id: int, email_thread: str) -> None:
    """
    Process actionables for an email in a detached manner (fire and forget).
    This function is designed to be called asynchronously without blocking the main request.
    """
    logger.info(f"Starting detached actionables processing for email_id: {email_id}")
    if not email_id:
        logger.error(
            "process_actionables_detached called with invalid email_id: {email_id}"
        )
        return

    try:
        await update_email_actionables_status(
            email_id, ActionablesProcessingStatus.PROCESSING
        )

        results = await process_actionables(email_id, email_thread)

        errors = []
        if isinstance(results.get("calendar"), Exception):
            errors.append(f"Calendar: {str(results['calendar'])}")
        if isinstance(results.get("notes"), Exception):
            errors.append(f"Notes: {str(results['notes'])}")
        if isinstance(results.get("shopping"), Exception):
            errors.append(f"Shopping: {str(results['shopping'])}")

        if errors:
            error_message = "; ".join(errors)
            await update_email_actionables_status(
                email_id, ActionablesProcessingStatus.FAILED, error_message
            )
            logger.error(
                f"Actionables processing failed for email {email_id}: {error_message}"
            )
        else:
            await update_email_actionables_status(
                email_id, ActionablesProcessingStatus.PROCESSED
            )
            logger.info(
                f"Successfully completed actionables processing for email {email_id}"
            )

    except Exception as e:
        error_message = f"Unexpected error during actionables processing: {str(e)}"
        await update_email_actionables_status(
            email_id, ActionablesProcessingStatus.FAILED, error_message
        )
        logger.critical(
            f"Critical error in actionables processing for email {email_id}: {error_message}",
            exc_info=e,
        )


async def process_actionables(email_id: int, email_thread: str) -> Dict[str, Any]:
    """
    Process all actionables from an email thread by running the agents in parallel.
    """
    logger.info(f"Processing actionables for email_id: {email_id}")

    try:
        from app.modules.actionables.agents.agent_service import AgentService

        agent_service = AgentService(email_id, email_thread)
        results = await agent_service.run_all_agents()

        calendar_results = results.get("calendar", {})
        notes_results = results.get("notes", {})
        shopping_results = results.get("shopping", {})

        if calendar_results.get("success"):
            logger.info(
                f"Calendar processing completed successfully for email_id {email_id}"
            )
        else:
            logger.error(
                f"Calendar processing failed for email_id {email_id}: {calendar_results.get('error', 'Unknown error')}"
            )

        if notes_results.get("success"):
            logger.info(
                f"Notes processing completed successfully for email_id {email_id}"
            )
        else:
            logger.error(
                f"Notes processing failed for email_id {email_id}: {notes_results.get('error', 'Unknown error')}"
            )

        if shopping_results.get("success"):
            logger.info(
                f"Shopping processing completed successfully for email_id {email_id}"
            )
        else:
            logger.error(
                f"Shopping processing failed for email_id {email_id}: {shopping_results.get('error', 'Unknown error')}"
            )

        logger.info(f"Finished processing actionables for email_id: {email_id}")
        return results

    except Exception as e:
        logger.critical(
            f"An unexpected error occurred during actionable processing for email_id: {email_id}",
            exc_info=e,
        )
        return {"error": "Failed to process actionables."}


def trigger_actionables_processing(email_id: int, email_thread: str) -> None:
    """
    Trigger actionables processing in a fire-and-forget manner.
    This is the function that should be called from the webhook processing.
    """

    asyncio.create_task(process_actionables_detached(email_id, email_thread))
    logger.info(f"Triggered background actionables processing for email_id: {email_id}")


async def get_email_thread_content(email_id: int) -> str:
    """
    Get the formatted email thread content for processing by agents.
    This creates a structured representation of the email thread.
    """
    try:
        async with get_db_transaction() as session:
            query = select(Email).where(Email.id == email_id)
            result = await session.execute(query)
            email = result.scalar_one_or_none()

            if not email:
                logger.error(f"Email with id {email_id} not found")
                return ""

            if email.thread_id:
                thread_query = (
                    select(Email)
                    .where(Email.thread_id == email.thread_id)
                    .order_by(Email.thread_position, Email.sent_at)
                )
                thread_result = await session.execute(thread_query)
                thread_emails = thread_result.scalars().all()
            else:
                thread_emails = [email]

            thread_content = {
                "thread_id": email.thread_id or f"single-{email.id}",
                "thread_subject": email.subject or "No Subject",
                "thread_messages": [],
            }

            for thread_email in thread_emails:
                message_data = {
                    "message_id": thread_email.message_id,
                    "message_subject": thread_email.subject,
                    "message_body": thread_email.text_body
                    or thread_email.html_body
                    or "",
                    "message_sender": thread_email.from_name or thread_email.from_email,
                    "message_sender_email": thread_email.from_email,
                    "message_sent_at": thread_email.sent_at.isoformat()
                    if thread_email.sent_at
                    else None,
                    "message_to_email": thread_email.original_recipient,
                }
                thread_content["thread_messages"].append(message_data)

            formatted_content = (
                f"Thread Subject: {thread_content['thread_subject']}\n\n"
            )

            for i, msg in enumerate(thread_content["thread_messages"], 1):
                formatted_content += f"Message {i}:\n"
                formatted_content += (
                    f"From: {msg['message_sender']} <{msg['message_sender_email']}>\n"
                )
                formatted_content += f"Subject: {msg['message_subject']}\n"
                if msg["message_sent_at"]:
                    formatted_content += f"Sent: {msg['message_sent_at']}\n"
                formatted_content += f"Body: {msg['message_body'][:1000]}...\n\n"

            return formatted_content

    except Exception as e:
        logger.error(
            f"Failed to get email thread content for email_id {email_id}: {str(e)}"
        )
        return f"Error retrieving email content: {str(e)}"
