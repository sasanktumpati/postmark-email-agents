import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import get_config
from app.modules.users.db import User
from app.modules.users.models.response import PostmarkEmailResponse
from app.modules.users.services import log_sent_email_with_silent_failure

logger = logging.getLogger(__name__)
settings = get_config()

POSTMARK_API_URL = "https://api.postmarkapp.com/email"


def get_welcome_email_html(name: str, api_key: str) -> str:
    """Load and format the welcome email HTML template."""
    template_path = Path(__file__).parent / "templates" / "email.html"

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        return template_content.format(name=name, api_key=api_key)

    except FileNotFoundError:
        logger.error(f"Email template not found at {template_path}")
        return f"""
        <html>
        <body>
            <h1>Welcome to Actionable Mail, {name}!</h1>
            <p>Your API Key: {api_key}</p>
            <p>Forward emails to: inbound+{name}@mail.built.systems</p>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error loading email template: {e}")
        return f"""
        <html>
        <body>
            <h1>Welcome to Actionable Mail, {name}!</h1>
            <p>Your API Key: {api_key}</p>
            <p>Forward emails to: inbound+{name}@mail.built.systems</p>
        </body>
        </html>
        """


def get_welcome_email_text(name: str, api_key: str) -> str:
    return f"""
Welcome to Actionable Mail, {name}!

Transform your inbox into an intelligent productivity hub. Our AI automatically extracts actionable items from your emails.

Your API Key:
{api_key}

Get Started in 2 Steps:

1. Send emails to your inbox:
   Forward emails to inbound+{name}@mail.built.systems

2. View your actionables:
   Login to Dashboard: https://email.built.systems

What our AI extracts:

Calendar Events: Meetings, appointments, deadlines
Reminders: Important tasks and follow-ups  
Notes: Key information to remember
Bills: Invoices, payments, and subscriptions
Coupons: Discount codes and promotional offers
Follow-ups: Required responses and check-ins

How it works:
Our AI agents automatically process your emails in real-time, intelligently categorizing and extracting actionable items. No more missed deadlines or forgotten discount codes.

---
Powered by Postmark (https://postmarkapp.com)
    """


async def send_welcome_email_async(
    user: User, fail_silently: bool = True, from_email: Optional[str] = None
) -> bool:
    if not user.api_key:
        error_msg = f"Cannot send welcome email to user {user.id}: API key is missing."
        logger.error(error_msg)
        if not fail_silently:
            raise ValueError(error_msg)
        return False

    sender_email = from_email or "app@built.systems"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": settings.postmark_api_key,
    }

    fallback_name = str(user.email).split("@")[0].strip()
    payload = {
        "From": f"Actionable Mail <{sender_email}>",
        "To": user.email,
        "Subject": "Welcome to Actionable Mail - Your AI-Powered Inbox is Ready!",
        "HtmlBody": get_welcome_email_html(user.name or fallback_name, user.api_key),
        "TextBody": get_welcome_email_text(user.name or fallback_name, user.api_key),
        "MessageStream": "email-agents",
    }

    postmark_response = PostmarkEmailResponse(error_code=-1, message="Unknown error")
    success = False

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Sending welcome email to {user.email}")
            response = await client.post(
                POSTMARK_API_URL, headers=headers, json=payload
            )
            response.raise_for_status()

            response_data = response.json()
            postmark_response = PostmarkEmailResponse(**response_data)
            success = True

            logger.info(
                f"Email sent successfully to {user.email}. MessageID: {postmark_response.message_id}"
            )

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error sending email to {user.email}: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)

        try:
            response_data = e.response.json()
            postmark_response = PostmarkEmailResponse(**response_data)
        except Exception:
            postmark_response = PostmarkEmailResponse(
                error_code=e.response.status_code,
                message=e.response.text,
            )

        if not fail_silently:
            raise

    except httpx.TimeoutException as e:
        error_msg = f"Timeout sending email to {user.email}: {str(e)}"
        logger.error(error_msg)
        postmark_response = PostmarkEmailResponse(
            error_code=-2,
            message=error_msg,
        )
        if not fail_silently:
            raise

    except Exception as e:
        error_msg = f"Unexpected error sending email to {user.email}: {str(e)}"
        logger.error(error_msg)
        postmark_response = PostmarkEmailResponse(
            error_code=-1,
            message=error_msg,
        )
        if not fail_silently:
            raise

    finally:
        try:
            await log_sent_email_with_silent_failure(
                user_id=user.id,
                from_email=sender_email,
                to_email=user.email,
                api_key=user.api_key,
                response=postmark_response,
                is_silent_failure=fail_silently and not success,
            )
        except Exception as log_error:
            logger.error(f"Failed to log email attempt: {log_error}")

    return success


def send_welcome_email_background(user: User, fail_silently: bool = True) -> None:
    async def send_email_task():
        try:
            await send_welcome_email_async(user, fail_silently)
        except Exception as e:
            logger.error(f"Background email sending failed for user {user.id}: {e}")

    asyncio.create_task(send_email_task())
    logger.info(f"Scheduled background welcome email for user {user.id}")
