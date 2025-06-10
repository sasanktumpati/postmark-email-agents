from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import select

from app.core.logger import get_logger

from .models import (
    Email,
    EmailAttachment,
    EmailRecipient,
    EmailSearchRequest,
    EmailThread,
    SpamStatus,
)

logger = get_logger(__name__)


class EmailRetrievalService:
    """Service for retrieving and searching emails."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        logger.debug("EmailRetrievalService initialized.")

    def _apply_user_filter(self, query, user_id: int):
        """Apply user filter to query using user_id for consistent security."""
        logger.debug(f"Applying user filter for user ID: {user_id}")
        return query.where(Email.user_id == user_id)

    def _validate_sort_column(self, sort_by: str) -> str:
        """Validate and return safe sort column to prevent SQL injection."""
        allowed_columns = {
            "sent_at",
            "processed_at",
            "from_email",
            "subject",
            "spam_score",
            "message_id",
            "id",
            "created_at",
        }
        if sort_by not in allowed_columns:
            logger.warning(
                f"Invalid sort column '{sort_by}' provided. Defaulting to 'sent_at'."
            )
            return "sent_at"
        logger.debug(f"Validated sort column: {sort_by}")
        return sort_by

    async def get_emails_with_pagination(
        self,
        user_id: int,
        page: int,
        limit: int,
        search_params: Optional[EmailSearchRequest] = None,
        sort_by: str = "sent_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Email], int]:
        """Get paginated list of emails with search and sorting."""
        logger.debug(
            f"Fetching emails for user ID: {user_id} with pagination. Page: {page}, Limit: {limit}"
        )

        if user_id <= 0:
            logger.error(f"Invalid user_id provided: {user_id}")
            raise ValueError("Invalid user_id")
        if page <= 0:
            page = 1
            logger.warning("Invalid page number provided. Defaulting to 1.")
        if limit <= 0 or limit > 100:
            limit = 20
            logger.warning("Invalid limit provided. Defaulting to 20.")

        query = select(Email).options(
            selectinload(Email.recipients),
            selectinload(Email.attachments),
            joinedload(Email.thread),
        )

        query = self._apply_user_filter(query, user_id)

        if search_params:
            logger.debug(f"Applying search filters: {search_params.model_dump_json()}")
            query = self._apply_search_filters(query, search_params)

        count_query = select(func.count(Email.id)).where(Email.user_id == user_id)

        if search_params:
            count_query = self._apply_search_filters(count_query, search_params)

        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()
        logger.debug(f"Total emails found for user ID {user_id}: {total_count}")

        sort_column_name = self._validate_sort_column(sort_by)
        sort_column = getattr(Email, sort_column_name)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
            logger.debug(f"Sorting by {sort_column_name} in descending order.")
        else:
            query = query.order_by(asc(sort_column))
            logger.debug(f"Sorting by {sort_column_name} in ascending order.")

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        logger.debug(f"Applying offset {offset} and limit {limit} to the query.")

        result = await self.db.execute(query)
        emails = result.scalars().all()
        logger.info(
            f"Retrieved {len(emails)} emails for user ID {user_id} on page {page}."
        )

        return list(emails), total_count

    async def get_email_by_id(self, email_id: int, user_id: int) -> Optional[Email]:
        """Get email by ID with all related data - secure user filtering."""
        logger.debug(f"Fetching email by ID: {email_id} for user ID: {user_id}")
        if user_id <= 0 or email_id <= 0:
            logger.warning(
                f"Invalid user_id ({user_id}) or email_id ({email_id}) provided. Returning None."
            )
            return None

        query = (
            select(Email)
            .options(
                selectinload(Email.recipients),
                selectinload(Email.attachments),
                selectinload(Email.headers),
                joinedload(Email.raw_email_entry),
                joinedload(Email.thread),
            )
            .where(Email.id == email_id, Email.user_id == user_id)
        )

        result = await self.db.execute(query)
        email = result.scalar_one_or_none()
        if email:
            logger.info(f"Email {email_id} found for user {user_id}.")
        else:
            logger.info(f"Email {email_id} not found for user {user_id}.")
        return email

    async def get_email_thread(self, email_id: int, user_id: int) -> List[Email]:
        """Get complete email thread for a given email ID - secure access."""
        logger.debug(
            f"Fetching email thread for email ID: {email_id} for user ID: {user_id}"
        )
        if user_id <= 0 or email_id <= 0:
            logger.warning(
                f"Invalid user_id ({user_id}) or email_id ({email_id}) provided. Returning empty list."
            )
            return []

        email = await self.get_email_by_id(email_id, user_id)

        if not email or not email.thread_id:
            logger.info(
                f"Email {email_id} not found or has no thread ID for user {user_id}. Returning empty list."
            )
            return []

        logger.debug(
            f"Email {email_id} belongs to thread {email.thread_id}. Fetching thread emails."
        )

        thread_emails_query = (
            select(Email)
            .options(
                selectinload(Email.recipients),
                selectinload(Email.attachments),
                selectinload(Email.headers),
                joinedload(Email.thread),
            )
            .where(Email.thread_id == email.thread_id, Email.user_id == user_id)
            .order_by(Email.thread_position, Email.sent_at)
        )

        result = await self.db.execute(thread_emails_query)
        emails = list(result.scalars().all())
        logger.info(
            f"Retrieved {len(emails)} emails in thread {email.thread_id} for user {user_id}."
        )
        return emails

    async def get_thread_by_id(
        self, thread_id: int, user_id: int
    ) -> Optional[EmailThread]:
        """Get thread by ID with user's emails only."""
        logger.debug(f"Fetching thread by ID: {thread_id} for user ID: {user_id}")
        if user_id <= 0 or thread_id <= 0:
            logger.warning(
                f"Invalid user_id ({user_id}) or thread_id ({thread_id}) provided. Returning None."
            )
            return None

        user_email_in_thread = await self.db.execute(
            select(Email.id)
            .where(Email.thread_id == thread_id, Email.user_id == user_id)
            .limit(1)
        )

        if not user_email_in_thread.scalar_one_or_none():
            logger.info(
                f"User {user_id} has no emails in thread {thread_id}. Returning None."
            )
            return None

        query = (
            select(EmailThread)
            .options(
                selectinload(EmailThread.emails).selectinload(Email.recipients),
                selectinload(EmailThread.emails).selectinload(Email.attachments),
                selectinload(EmailThread.emails).selectinload(Email.headers),
            )
            .where(EmailThread.id == thread_id)
        )

        result = await self.db.execute(query)
        thread = result.scalar_one_or_none()

        if thread:
            thread.emails = [
                email for email in thread.emails if email.user_id == user_id
            ]
            logger.info(
                f"Thread {thread_id} retrieved for user {user_id}. Contains {len(thread.emails)} emails."
            )
        else:
            logger.info(f"Thread {thread_id} not found.")

        return thread

    async def get_emails_by_thread_id(
        self, thread_id: int, user_id: int
    ) -> List[Email]:
        """Get user's emails in a specific thread ordered by position."""
        logger.debug(
            f"Fetching emails by thread ID: {thread_id} for user ID: {user_id}"
        )
        if user_id <= 0 or thread_id <= 0:
            logger.warning(
                f"Invalid user_id ({user_id}) or thread_id ({thread_id}) provided. Returning empty list."
            )
            return []

        query = (
            select(Email)
            .options(
                selectinload(Email.recipients),
                selectinload(Email.attachments),
                selectinload(Email.headers),
            )
            .where(Email.thread_id == thread_id, Email.user_id == user_id)
            .order_by(Email.thread_position, Email.sent_at)
        )

        result = await self.db.execute(query)
        emails = list(result.scalars().all())
        logger.info(
            f"Retrieved {len(emails)} emails for thread {thread_id} and user {user_id}."
        )
        return emails

    async def _find_root_email(self, email: Email, user_id: int) -> Email:
        """Find the root email of a thread - only within user's emails."""
        logger.debug(
            f"Finding root email for email ID: {email.id} for user ID: {user_id}"
        )
        current_email = email

        while current_email.parent_email_id:
            query = select(Email).where(
                Email.id == current_email.parent_email_id,
                Email.user_id == user_id,
            )
            result = await self.db.execute(query)
            parent = result.scalar_one_or_none()
            if not parent:
                logger.debug(
                    f"Parent email not found for {current_email.id}. Breaking loop."
                )
                break
            current_email = parent
        logger.debug(f"Root email found for email ID {email.id}: {current_email.id}")
        return current_email

    async def _get_thread_emails(self, root_email_id: int, user_id: int) -> List[Email]:
        """Get all user's emails in a thread starting from root email."""
        logger.debug(
            f"Getting thread emails from root {root_email_id} for user ID: {user_id}"
        )
        if user_id <= 0 or root_email_id <= 0:
            logger.warning(
                f"Invalid user_id ({user_id}) or root_email_id ({root_email_id}) provided. Returning empty list."
            )
            return []

        collected_ids = set()
        to_process = [root_email_id]

        while to_process:
            current_id = to_process.pop(0)
            if current_id in collected_ids:
                continue

            collected_ids.add(current_id)

            children_query = select(Email.id).where(
                Email.parent_email_id == current_id,
                Email.user_id == user_id,
            )
            result = await self.db.execute(children_query)
            child_ids = [row[0] for row in result.fetchall()]
            logger.debug(f"Found {len(child_ids)} children for email ID {current_id}.")
            to_process.extend(child_ids)

        if not collected_ids:
            logger.info(
                f"No emails collected for thread starting from root {root_email_id} for user {user_id}. Returning empty list."
            )
            return []

        emails_query = (
            select(Email)
            .options(
                selectinload(Email.recipients),
                selectinload(Email.attachments),
                selectinload(Email.headers),
            )
            .where(Email.id.in_(collected_ids), Email.user_id == user_id)
            .order_by(Email.sent_at)
        )

        result = await self.db.execute(emails_query)
        return list(result.scalars().all())

    def _apply_search_filters(self, query, search_params: EmailSearchRequest):
        """Apply search filters to query with proper validation."""
        conditions = []

        if search_params.query:
            search_term = search_params.query.strip()[:500]
            if search_term:
                search_pattern = f"%{search_term}%"
                text_conditions = [
                    Email.subject.ilike(search_pattern),
                    Email.from_email.ilike(search_pattern),
                    Email.from_name.ilike(search_pattern),
                ]
                conditions.append(or_(*text_conditions))

        if search_params.from_email:
            from_email = search_params.from_email.strip()[:320]
            if from_email:
                conditions.append(Email.from_email.ilike(f"%{from_email}%"))

        if search_params.subject:
            subject = search_params.subject.strip()[:500]
            if subject:
                conditions.append(Email.subject.ilike(f"%{subject}%"))

        if search_params.tag:
            tag = search_params.tag.strip()[:255]
            if tag:
                conditions.append(Email.tag == tag)

        if search_params.message_stream:
            stream = search_params.message_stream.strip()[:100]
            if stream:
                conditions.append(Email.message_stream == stream)

        if search_params.spam_status:
            try:
                spam_enum = SpamStatus(search_params.spam_status.lower())
                conditions.append(Email.spam_status == spam_enum)
            except ValueError:
                pass

        if search_params.date_from:
            from datetime import datetime

            try:
                date_from = datetime.fromisoformat(
                    search_params.date_from.replace("Z", "+00:00")
                )
                conditions.append(Email.sent_at >= date_from)
            except ValueError:
                pass

        if search_params.date_to:
            from datetime import datetime

            try:
                date_to = datetime.fromisoformat(
                    search_params.date_to.replace("Z", "+00:00")
                )
                conditions.append(Email.sent_at <= date_to)
            except ValueError:
                pass

        if search_params.to_email:
            to_email = search_params.to_email.strip()[:320]
            if to_email:
                recipient_subquery = select(EmailRecipient.email_id).where(
                    EmailRecipient.email_address.ilike(f"%{to_email}%")
                )
                conditions.append(Email.id.in_(recipient_subquery))

        if search_params.has_attachments is not None:
            attachment_subquery = select(EmailAttachment.email_id).distinct()
            if search_params.has_attachments:
                conditions.append(Email.id.in_(attachment_subquery))
            else:
                conditions.append(~Email.id.in_(attachment_subquery))

        if conditions:
            query = query.where(and_(*conditions))
        return query

    async def search_emails(
        self,
        user_id: int,
        search_params: EmailSearchRequest,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Email], int]:
        """Search emails with pagination - secure user filtering."""
        return await self.get_emails_with_pagination(
            user_id=user_id,
            page=page,
            limit=limit,
            search_params=search_params,
        )

    async def get_email_stats(self, user_id: int) -> Dict[str, int]:
        """Get email statistics for user."""
        if user_id <= 0:
            return {
                "total_emails": 0,
                "non_spam_emails": 0,
                "spam_emails": 0,
                "unique_senders": 0,
            }

        base_query = select(func.count(Email.id)).where(Email.user_id == user_id)

        total_query = base_query
        non_spam_query = base_query.where(Email.spam_status != SpamStatus.YES)
        spam_query = base_query.where(Email.spam_status == SpamStatus.YES)
        unique_senders_query = select(
            func.count(func.distinct(Email.from_email))
        ).where(Email.user_id == user_id)

        total_result, non_spam_result, spam_result, unique_senders_result = (
            await self.db.execute(total_query),
            await self.db.execute(non_spam_query),
            await self.db.execute(spam_query),
            await self.db.execute(unique_senders_query),
        )

        return {
            "total_emails": total_result.scalar() or 0,
            "non_spam_emails": non_spam_result.scalar() or 0,
            "spam_emails": spam_result.scalar() or 0,
            "unique_senders": unique_senders_result.scalar() or 0,
        }

    async def get_recent_emails(self, user_id: int, limit: int = 10) -> List[Email]:
        """Get most recent emails for user."""
        if user_id <= 0:
            return []
        if limit <= 0 or limit > 50:
            limit = 10

        query = (
            select(Email)
            .options(
                selectinload(Email.recipients),
                selectinload(Email.attachments),
            )
            .where(Email.user_id == user_id)
            .order_by(desc(Email.sent_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_emails_by_sender(
        self, user_id: int, sender_email: str, limit: int = 50
    ) -> List[Email]:
        """Get emails from a specific sender for user."""
        if user_id <= 0:
            return []
        if limit <= 0 or limit > 100:
            limit = 50

        sender_email = sender_email.strip()[:320]
        if not sender_email:
            return []

        query = (
            select(Email)
            .where(
                Email.user_id == user_id,
                Email.from_email.ilike(f"%{sender_email}%"),
            )
            .order_by(desc(Email.sent_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_emails_with_attachments(
        self, user_id: int, page: int = 1, limit: int = 20
    ) -> Tuple[List[Email], int]:
        """Get paginated list of emails with attachments for user."""
        if user_id <= 0:
            return [], 0
        if page <= 0:
            page = 1
        if limit <= 0 or limit > 100:
            limit = 20

        attachment_subquery = select(EmailAttachment.email_id).distinct()
        query = (
            select(Email)
            .where(
                Email.user_id == user_id,
                Email.id.in_(attachment_subquery),
            )
            .options(selectinload(Email.attachments))
        )

        count_query = select(func.count(Email.id)).where(
            Email.user_id == user_id,
            Email.id.in_(attachment_subquery),
        )

        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        offset = (page - 1) * limit
        query = query.order_by(desc(Email.sent_at)).offset(offset).limit(limit)

        result = await self.db.execute(query)
        emails = result.scalars().all()

        return list(emails), total_count


async def get_email_service(db_session: AsyncSession) -> EmailRetrievalService:
    """Factory function to get an instance of EmailService."""
    return EmailRetrievalService(db_session)
