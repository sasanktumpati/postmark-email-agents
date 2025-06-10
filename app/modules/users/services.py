import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional, Tuple, Union

from itsdangerous import BadSignature, TimestampSigner

from app.core.config import get_config
from app.core.db.database import get_db_session
from app.core.logger import get_logger
from app.modules.users.db import User
from app.modules.users.models.response import PostmarkEmailResponse
from app.modules.users.repository import sent_email_repository, user_repository

logger = get_logger(__name__)
settings = get_config()


signer = TimestampSigner(settings.secret_key, salt=settings.api_key_salt)
logger.debug("TimestampSigner initialized for API key generation.")


def generate_api_key(user_id: int) -> str:
    """
    Generates a secure, signed API key for a user.
    Uses HMAC-SHA256 for stronger security.
    """
    logger.debug(f"Generating API key for user ID: {user_id}")

    random_component = secrets.token_urlsafe(16)

    payload = f"{user_id}:{random_component}"

    api_key = signer.sign(payload.encode()).decode()
    logger.info(f"API key generated for user ID: {user_id}")
    return api_key


def verify_api_key(api_key: str) -> Optional[int]:
    """
    Verifies an API key.
    Returns the user_id if the key is valid, otherwise None.
    Enhanced with better error handling and security logging.
    """
    logger.debug(f"Verifying API key (truncated): {api_key[:8]}...")
    if not api_key or len(api_key) < 10:
        logger.warning("API key too short or empty for verification.")
        return None

    try:
        payload = signer.unsign(api_key, max_age=None).decode()

        user_id_str = payload.split(":", 1)[0]
        user_id = int(user_id_str)

        if user_id <= 0:
            logger.warning(f"Invalid user ID in API key: {user_id}")
            return None

        logger.info(f"API key verified successfully for user ID: {user_id}")
        return user_id

    except BadSignature:
        logger.warning(f"Invalid API key signature received: {api_key[:8]}...")
        return None
    except (ValueError, TypeError, IndexError) as e:
        logger.error(
            f"Could not parse user ID from API key (truncated): {api_key[:8]}... - {str(e)}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error during API key verification (truncated): {api_key[:8]}... - {str(e)}"
        )
        return None


def hash_api_key_for_storage(api_key: str) -> str:
    """
    Hash API key for secure storage (optional enhancement).
    This would be used if we want to store hashed API keys instead of plain text.
    """
    logger.debug("Hashing API key for storage.")
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
    """
    Verify API key against stored hash.
    """
    logger.debug("Verifying API key against stored hash.")
    return hmac.compare_digest(hash_api_key_for_storage(api_key), stored_hash)


async def get_or_create_user_by_email_and_mailbox(
    email: str, mailbox_hash: str, name: str
) -> Tuple[User, bool]:
    """
    Get or create user by email and mailbox hash.
    Returns (user, created) tuple.
    Enhanced with better error handling and validation.
    """
    logger.debug(
        f"Attempting to get or create user by email: {email} and mailbox hash: {mailbox_hash}"
    )

    if not email or not email.strip():
        logger.error(
            "Email address is required for get_or_create_user_by_email_and_mailbox."
        )
        raise ValueError("Email address is required")

    if not mailbox_hash or not mailbox_hash.strip():
        logger.error(
            "Mailbox hash is required for get_or_create_user_by_email_and_mailbox."
        )
        raise ValueError("Mailbox hash is required")

    email = email.strip().lower()
    name = name.strip() if name else ""

    async with get_db_session() as session:
        try:
            user, created = await user_repository.get_or_create_user(
                session, email, mailbox_hash, name
            )

            if created and not user.api_key:
                logger.debug(f"New user {user.email} created. Generating API key.")
                await session.flush()
                await session.refresh(user)

                api_key = generate_api_key(user.id)
                user.api_key = api_key
                await user_repository.update(session, user)

                logger.info(
                    f"Created new user: {user.email} with ID: {user.id} and generated API key."
                )

            await session.commit()
            logger.debug(
                f"User {user.email} (created: {created}) processed successfully."
            )
            return user, created

        except Exception as e:
            await session.rollback()
            logger.error(
                f"Error in get_or_create_user_by_email_and_mailbox for email {email}: {e}"
            )
            raise


async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email address with input validation."""
    logger.debug(f"Attempting to get user by email: {email}")
    if not email or not email.strip():
        logger.warning("Email address is empty or invalid for get_user_by_email.")
        return None

    email = email.strip().lower()
    async with get_db_session() as session:
        user = await user_repository.get_by_email(session, email)
        if user:
            logger.debug(f"User {email} found.")
        else:
            logger.debug(f"User {email} not found.")
        return user


async def get_user_by_mailbox_hash(mailbox_hash: str) -> Optional[User]:
    """
    Get user by mailbox hash with input validation.
    """
    logger.debug(f"Attempting to get user by mailbox hash: {mailbox_hash}")
    if not mailbox_hash or not mailbox_hash.strip():
        logger.warning("Mailbox hash is empty or invalid for get_user_by_mailbox_hash.")
        return None

    async with get_db_session() as session:
        user = await user_repository.get_by_mailbox_hash(session, mailbox_hash)
        if user:
            logger.debug(f"User with mailbox hash {mailbox_hash} found.")
        else:
            logger.debug(f"User with mailbox hash {mailbox_hash} not found.")
        return user


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
    Enhanced with better error handling.
    """
    logger.debug(
        f"Logging sent email for user_id: {user_id}, to: {to_email}. Silent failure: {is_silent_failure}"
    )
    if user_id <= 0:
        logger.error(f"Invalid user_id for email logging: {user_id}. Skipping logging.")
        return

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
                    f"Silent email failure logged for user {user_id} to {to_email}. Error: {message}"
                )
            else:
                error_code = (
                    response.get("ErrorCode", 0)
                    if isinstance(response, dict)
                    else response.error_code
                )
                status_str = "sent" if error_code == 0 else "failed"
                logger.info(f"Email {status_str} for user {user_id} to {to_email}.")

        except Exception as e:
            await session.rollback()
            logger.error(
                f"Error logging sent email for user {user_id} to {to_email}: {e}"
            )
