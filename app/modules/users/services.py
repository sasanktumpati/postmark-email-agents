import logging
from typing import Any, Dict, Optional, Tuple, Union

from itsdangerous import BadSignature, Signer

from app.core.config import get_config
from app.core.db.database import get_db_session
from app.modules.users.db import User
from app.modules.users.models.response import PostmarkEmailResponse
from app.modules.users.repository import sent_email_repository, user_repository

logger = logging.getLogger(__name__)
settings = get_config()


signer = Signer(settings.secret_key, salt=settings.api_key_salt)


def generate_api_key(user_id: int) -> str:
    """Generates a secure, signed API key for a user."""
    return signer.sign(str(user_id).encode()).decode()


def verify_api_key(api_key: str) -> Optional[int]:
    """
    Verifies an API key.
    Returns the user_id if the key is valid, otherwise None.
    """
    try:
        user_id = signer.unsign(api_key).decode()
        return int(user_id)
    except BadSignature:
        logger.warning(f"Invalid API key signature received: {api_key}")
        return None
    except (ValueError, TypeError):
        logger.error(f"Could not parse user ID from API key: {api_key}")
        return None


async def get_or_create_user_by_email_and_mailbox(
    email: str, mailbox_hash: str
) -> Tuple[User, bool]:
    """
    Get or create user by email and mailbox hash.
    Returns (user, created) tuple.
    """
    async with get_db_session() as session:
        try:
            user, created = await user_repository.get_or_create_user(
                session, email, mailbox_hash
            )

            if created and not user.api_key:
                await session.flush()
                await session.refresh(user)

                api_key = generate_api_key(user.id)
                user.api_key = api_key
                await user_repository.update(session, user)

                logger.info(f"Created new user: {user.email} with ID: {user.id}")

            await session.commit()
            return user, created

        except Exception as e:
            await session.rollback()
            logger.error(f"Error in get_or_create_user_by_email_and_mailbox: {e}")
            raise


async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email address."""
    async with get_db_session() as session:
        return await user_repository.get_by_email(session, email)


async def get_user_by_mailbox_hash(mailbox_hash: str) -> Optional[User]:
    """Get user by mailbox hash."""
    async with get_db_session() as session:
        return await user_repository.get_by_mailbox_hash(session, mailbox_hash)


async def log_sent_email_with_silent_failure(
    user_id: int,
    from_email: str,
    to_email: str,
    api_key: str,
    response: Union[Dict[str, Any], PostmarkEmailResponse],
    is_silent_failure: bool = False,
) -> None:
    """
    Log sent email attempt with silent failure support.
    This function manages its own database session.
    """
    async with get_db_session() as session:
        try:
            response_dict = (
                response.model_dump(by_alias=True)
                if isinstance(response, PostmarkEmailResponse)
                else response
            )

            await sent_email_repository.log_email_attempt(
                session=session,
                user_id=user_id,
                from_email=from_email,
                to_email=to_email,
                api_key=api_key,
                response=response_dict,
                is_silent_failure=is_silent_failure,
            )
            await session.commit()

            if is_silent_failure:
                error_code = (
                    response.get("ErrorCode", 0)
                    if isinstance(response, dict)
                    else response.error_code
                )
                message = (
                    response.get("Message", "Unknown error")
                    if isinstance(response, dict)
                    else response.message
                )
                logger.warning(
                    f"Silent email failure logged for user {user_id}: {message}"
                )
            else:
                error_code = (
                    response.get("ErrorCode", 0)
                    if isinstance(response, dict)
                    else response.error_code
                )
                status = "sent" if error_code == 0 else "failed"
                logger.info(f"Email {status} for user {user_id}: {to_email}")

        except Exception as e:
            await session.rollback()
            logger.error(f"Error logging sent email: {e}")
