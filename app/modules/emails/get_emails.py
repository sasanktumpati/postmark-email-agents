from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import select

from .models import (
    Email,
    EmailAttachment,
    EmailRecipient,
    EmailSearchRequest,
    SpamStatus,
)


class EmailRetrievalService:
    """Service for retrieving and searching emails."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_emails_with_pagination(
        self,
        page: int,
        limit: int,
        search_params: Optional[EmailSearchRequest] = None,
        sort_by: str = "sent_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Email], int]:
        """Get paginated list of emails with search and sorting."""

        query = select(Email).options(
            selectinload(Email.recipients), selectinload(Email.attachments)
        )

        if search_params:
            query = self._apply_search_filters(query, search_params)

        count_query = select(func.count(Email.id))
        if search_params:
            count_query = self._apply_search_filters(count_query, search_params)

        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()

        if hasattr(Email, sort_by):
            sort_column = getattr(Email, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        emails = result.scalars().all()

        return list(emails), total_count

    async def get_email_by_id(self, email_id: int) -> Optional[Email]:
        """Get email by ID with all related data."""
        query = (
            select(Email)
            .options(
                selectinload(Email.recipients),
                selectinload(Email.attachments),
                selectinload(Email.headers),
                joinedload(Email.raw_email_entry),
            )
            .where(Email.id == email_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_email_thread(self, email_id: int) -> List[Email]:
        """Get complete email thread for a given email ID."""
        email = await self.get_email_by_id(email_id)
        if not email:
            return []

        root_email = await self._find_root_email(email)

        thread_emails = await self._get_thread_emails(root_email.id)

        return thread_emails

    async def _find_root_email(self, email: Email) -> Email:
        """Find the root email of a thread."""
        current_email = email

        while current_email.parent_email_id:
            query = select(Email).where(Email.id == current_email.parent_email_id)
            result = await self.db.execute(query)
            parent = result.scalar_one_or_none()
            if not parent:
                break
            current_email = parent

        return current_email

    async def _get_thread_emails(self, root_email_id: int) -> List[Email]:
        """Get all emails in a thread starting from root email."""
        collected_ids = set()
        to_process = [root_email_id]

        while to_process:
            current_id = to_process.pop(0)
            if current_id in collected_ids:
                continue

            collected_ids.add(current_id)

            children_query = select(Email.id).where(Email.parent_email_id == current_id)
            result = await self.db.execute(children_query)
            child_ids = [row[0] for row in result.fetchall()]
            to_process.extend(child_ids)

        if not collected_ids:
            return []

        emails_query = (
            select(Email)
            .options(
                selectinload(Email.recipients),
                selectinload(Email.attachments),
                selectinload(Email.headers),
            )
            .where(Email.id.in_(collected_ids))
            .order_by(Email.sent_at)
        )

        result = await self.db.execute(emails_query)
        return list(result.scalars().all())

    def _apply_search_filters(self, query, search_params: EmailSearchRequest):
        """Apply search filters to query."""
        conditions = []

        if search_params.query:
            search_term = f"%{search_params.query}%"
            text_conditions = [
                Email.subject.ilike(search_term),
                Email.from_email.ilike(search_term),
                Email.from_name.ilike(search_term),
            ]
            conditions.append(or_(*text_conditions))

        if search_params.from_email:
            conditions.append(Email.from_email.ilike(f"%{search_params.from_email}%"))

        if search_params.subject:
            conditions.append(Email.subject.ilike(f"%{search_params.subject}%"))

        if search_params.mailbox_hash:
            conditions.append(Email.mailbox_hash == search_params.mailbox_hash)

        if search_params.tag:
            conditions.append(Email.tag == search_params.tag)

        if search_params.message_stream:
            conditions.append(Email.message_stream == search_params.message_stream)

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
            recipient_subquery = select(EmailRecipient.email_id).where(
                EmailRecipient.email_address.ilike(f"%{search_params.to_email}%")
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
        self, search_params: EmailSearchRequest, page: int = 1, limit: int = 20
    ) -> Tuple[List[Email], int]:
        """Search emails with advanced filters."""
        return await self.get_emails_with_pagination(
            page=page, limit=limit, search_params=search_params
        )

    async def get_email_stats(self) -> Dict[str, int]:
        """Get email statistics."""
        stats_query = select(
            func.count(Email.id).label("total_emails"),
            func.count(Email.id)
            .filter(Email.spam_status == SpamStatus.NO)
            .label("non_spam_emails"),
            func.count(Email.id)
            .filter(Email.spam_status == SpamStatus.YES)
            .label("spam_emails"),
            func.count(func.distinct(Email.from_email)).label("unique_senders"),
        )

        result = await self.db.execute(stats_query)
        row = result.fetchone()

        return {
            "total_emails": row.total_emails,
            "non_spam_emails": row.non_spam_emails,
            "spam_emails": row.spam_emails,
            "unique_senders": row.unique_senders,
        }

    async def get_recent_emails(self, limit: int = 10) -> List[Email]:
        """Get most recent emails."""
        query = (
            select(Email)
            .options(selectinload(Email.recipients), selectinload(Email.attachments))
            .order_by(desc(Email.processed_at))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_emails_by_sender(
        self, sender_email: str, limit: int = 50
    ) -> List[Email]:
        """Get emails from a specific sender."""
        query = (
            select(Email)
            .options(selectinload(Email.recipients), selectinload(Email.attachments))
            .where(Email.from_email.ilike(f"%{sender_email}%"))
            .order_by(desc(Email.sent_at))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_emails_with_attachments(
        self, page: int = 1, limit: int = 20
    ) -> Tuple[List[Email], int]:
        """Get emails that have attachments."""
        attachment_subquery = select(EmailAttachment.email_id).distinct()

        query = (
            select(Email)
            .options(selectinload(Email.recipients), selectinload(Email.attachments))
            .where(Email.id.in_(attachment_subquery))
            .order_by(desc(Email.sent_at))
        )

        count_query = select(func.count(Email.id)).where(
            Email.id.in_(attachment_subquery)
        )

        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        emails = result.scalars().all()

        return list(emails), total_count


async def get_email_service(db_session: AsyncSession) -> EmailRetrievalService:
    """Factory function to create email retrieval service."""
    return EmailRetrievalService(db_session)
