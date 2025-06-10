import hashlib
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
    EmailThread,
    EmailThreadSearchRequest,
    RecipientType,
)

logger = get_logger(__name__)


class EmailThreadService:
    """Service for managing email threads."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        logger.debug("EmailThreadService initialized.")

    def generate_thread_id(self, subject: str, participants: List[str]) -> str:
        """Generate a unique thread ID based on subject and participants."""

        normalized_subject = self._normalize_subject(subject)

        sorted_participants = sorted(participants)

        thread_data = f"{normalized_subject}:{':'.join(sorted_participants)}"
        return hashlib.md5(thread_data.encode()).hexdigest()

    def _normalize_subject(self, subject: str) -> str:
        """Normalize email subject for thread grouping."""
        if not subject:
            return ""

        prefixes = ["re:", "fwd:", "fw:", "forward:", "reply:"]
        normalized = subject.strip().lower()

        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :].strip()

        return normalized

    async def create_or_get_thread(
        self,
        subject: str,
        participants: List[str],
        thread_summary: Optional[str] = None,
    ) -> EmailThread:
        """Create a new thread or get existing one based on subject and participants."""
        thread_id = self.generate_thread_id(subject, participants)

        result = await self.db.execute(
            select(EmailThread).where(EmailThread.thread_id == thread_id)
        )
        existing_thread = result.scalar_one_or_none()

        if existing_thread:
            logger.debug(
                f"Using existing thread {existing_thread.id} for subject: {subject}"
            )
            return existing_thread

        new_thread = EmailThread(
            thread_id=thread_id,
            subject=subject,
            thread_summary=thread_summary or f"Email thread: {subject or 'No subject'}",
            email_count=0,
        )

        self.db.add(new_thread)
        await self.db.flush()
        await self.db.refresh(new_thread)
        logger.info(f"Created new thread {new_thread.id} for subject: {subject}")

        return new_thread

    async def add_email_to_thread(self, email: Email, thread: EmailThread) -> None:
        """Add an email to a thread and update thread metadata."""

        email.thread_id = thread.id

        current_max_position = await self.db.execute(
            select(func.max(Email.thread_position)).where(Email.thread_id == thread.id)
        )
        max_position = current_max_position.scalar() or -1
        email.thread_position = max_position + 1

        thread.email_count += 1
        thread.updated_at = func.now()

        if thread.first_email_id is None:
            thread.first_email_id = email.id
        thread.last_email_id = email.id

        await self.db.flush()
        logger.debug(
            f"Added email {email.id} to thread {thread.id} at position {email.thread_position}"
        )

    async def get_thread_participants(self, thread_id: int) -> List[str]:
        """Get all unique participants in a thread."""
        result = await self.db.execute(
            select(EmailRecipient.email_address)
            .join(Email, EmailRecipient.email_id == Email.id)
            .where(Email.thread_id == thread_id)
            .distinct()
        )
        participants = [row[0] for row in result.fetchall()]
        logger.debug(f"Found {len(participants)} participants in thread {thread_id}")
        return participants

    async def get_threads_with_pagination(
        self,
        page: int,
        limit: int,
        search_params: Optional[EmailThreadSearchRequest] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> Tuple[List[EmailThread], int]:
        """Get paginated list of threads with search and sorting."""

        query = select(EmailThread).options(
            selectinload(EmailThread.emails),
            joinedload(EmailThread.first_email),
            joinedload(EmailThread.last_email),
        )

        if search_params:
            query = self._apply_thread_search_filters(query, search_params)

        count_query = select(func.count(EmailThread.id))
        if search_params:
            count_query = self._apply_thread_search_filters(count_query, search_params)

        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()

        if hasattr(EmailThread, sort_by):
            sort_column = getattr(EmailThread, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        threads = result.scalars().all()
        logger.info(
            f"Retrieved {len(threads)} threads (total: {total_count}) for page {page}"
        )

        return list(threads), total_count

    def _apply_thread_search_filters(
        self, query, search_params: EmailThreadSearchRequest
    ):
        """Apply search filters to thread query."""
        conditions = []

        if search_params.query:
            search_term = f"%{search_params.query}%"
            text_conditions = [
                EmailThread.subject.ilike(search_term),
                EmailThread.thread_summary.ilike(search_term),
            ]
            conditions.append(or_(*text_conditions))

        if search_params.subject:
            conditions.append(EmailThread.subject.ilike(f"%{search_params.subject}%"))

        if search_params.thread_summary:
            conditions.append(
                EmailThread.thread_summary.ilike(f"%{search_params.thread_summary}%")
            )

        if search_params.min_email_count:
            conditions.append(EmailThread.email_count >= search_params.min_email_count)

        if search_params.max_email_count:
            conditions.append(EmailThread.email_count <= search_params.max_email_count)

        if search_params.date_from:
            from datetime import datetime

            try:
                date_from = datetime.fromisoformat(
                    search_params.date_from.replace("Z", "+00:00")
                )
                conditions.append(EmailThread.created_at >= date_from)
            except ValueError:
                logger.warning(f"Invalid date_from format: {search_params.date_from}")
                pass

        if search_params.date_to:
            from datetime import datetime

            try:
                date_to = datetime.fromisoformat(
                    search_params.date_to.replace("Z", "+00:00")
                )
                conditions.append(EmailThread.created_at <= date_to)
            except ValueError:
                logger.warning(f"Invalid date_to format: {search_params.date_to}")
                pass

        if search_params.updated_from:
            from datetime import datetime

            try:
                updated_from = datetime.fromisoformat(
                    search_params.updated_from.replace("Z", "+00:00")
                )
                conditions.append(EmailThread.updated_at >= updated_from)
            except ValueError:
                logger.warning(
                    f"Invalid updated_from format: {search_params.updated_from}"
                )
                pass

        if search_params.updated_to:
            from datetime import datetime

            try:
                updated_to = datetime.fromisoformat(
                    search_params.updated_to.replace("Z", "+00:00")
                )
                conditions.append(EmailThread.updated_at <= updated_to)
            except ValueError:
                logger.warning(f"Invalid updated_to format: {search_params.updated_to}")
                pass

        if conditions:
            query = query.where(and_(*conditions))

        return query

    async def get_thread_by_id(self, thread_id: int) -> Optional[EmailThread]:
        """Get thread by ID with all related data."""
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
        return result.scalar_one_or_none()

    async def update_thread_summary(self, thread_id: int, summary: str) -> bool:
        """Update thread summary."""
        result = await self.db.execute(
            select(EmailThread).where(EmailThread.id == thread_id)
        )
        thread = result.scalar_one_or_none()

        if not thread:
            logger.warning(f"Thread {thread_id} not found for summary update")
            return False

        thread.thread_summary = summary
        thread.updated_at = func.now()
        await self.db.commit()
        logger.info(f"Updated summary for thread {thread_id}")

        return True

    async def get_thread_stats(self) -> Dict[str, int]:
        """Get thread statistics."""
        stats_query = select(
            func.count(EmailThread.id).label("total_threads"),
            func.count(EmailThread.id)
            .filter(EmailThread.email_count == 1)
            .label("single_email_threads"),
            func.count(EmailThread.id)
            .filter(EmailThread.email_count > 1)
            .label("multi_email_threads"),
            func.avg(EmailThread.email_count).label("avg_emails_per_thread"),
        )

        result = await self.db.execute(stats_query)
        row = result.fetchone()

        threads_with_attachments_query = select(
            func.count(func.distinct(EmailThread.id))
        ).select_from(
            EmailThread.__table__.join(Email.__table__).join(EmailAttachment.__table__)
        )

        attachments_result = await self.db.execute(threads_with_attachments_query)
        threads_with_attachments = attachments_result.scalar() or 0

        most_active_query = (
            select(EmailThread.thread_id, EmailThread.email_count)
            .order_by(desc(EmailThread.email_count))
            .limit(1)
        )

        most_active_result = await self.db.execute(most_active_query)
        most_active_row = most_active_result.fetchone()

        return {
            "total_threads": row.total_threads or 0,
            "threads_with_single_email": row.single_email_threads or 0,
            "threads_with_multiple_emails": row.multi_email_threads or 0,
            "average_emails_per_thread": float(row.avg_emails_per_thread or 0),
            "threads_with_attachments": threads_with_attachments,
            "most_active_thread_id": most_active_row[0] if most_active_row else None,
            "most_active_thread_email_count": most_active_row[1]
            if most_active_row
            else 0,
        }

    async def migrate_existing_emails_to_threads(self) -> Dict[str, int]:
        """Migrate existing emails to the new thread system."""
        migration_stats = {
            "emails_processed": 0,
            "threads_created": 0,
            "emails_with_threads": 0,
        }

        emails_query = (
            select(Email)
            .options(selectinload(Email.recipients))
            .where(Email.thread_id.is_(None))
        )

        result = await self.db.execute(emails_query)
        emails = result.scalars().all()

        for email in emails:
            migration_stats["emails_processed"] += 1

            participants = [
                recipient.email_address
                for recipient in email.recipients
                if recipient.recipient_type in [RecipientType.FROM, RecipientType.TO]
            ]

            if not participants:
                participants = [email.from_email]

            thread = await self.create_or_get_thread(
                subject=email.subject or "",
                participants=participants,
                thread_summary=f"Thread for: {email.subject or 'No subject'}",
            )

            if thread.email_count == 0:
                migration_stats["threads_created"] += 1

            await self.add_email_to_thread(email, thread)
            migration_stats["emails_with_threads"] += 1

        await self.db.commit()
        return migration_stats


async def get_thread_service(db_session: AsyncSession) -> EmailThreadService:
    """Factory function to create email thread service."""
    return EmailThreadService(db_session)
