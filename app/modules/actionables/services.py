from typing import List, Tuple

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.db import get_async_db
from app.core.logger import get_logger
from app.modules.actionables.api import (
    ActionableListRequest,
    ActionableObject,
    ActionableType,
    BillResponse,
    CalendarEventResponse,
    CouponResponse,
    EmailNoteResponse,
    EmailReminderResponse,
    FollowUpResponse,
)
from app.modules.actionables.calendar.db import CalendarEvent, EmailReminder, FollowUp
from app.modules.actionables.notes.db import EmailNote
from app.modules.actionables.shopping.db import Bill, Coupon
from app.modules.emails.models.db import Email

logger = get_logger(__name__)


class ActionableService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        logger.debug("ActionableService initialized.")

    async def list_actionables(
        self, request: ActionableListRequest, user_id: int
    ) -> Tuple[List[ActionableObject], int]:
        logger.debug(f"Listing actionables for user ID: {user_id}")

        if user_id <= 0:
            logger.error(f"Invalid user_id provided: {user_id}")
            raise ValueError("Invalid user_id")

        if request.page <= 0:
            request.page = 1
        if request.limit <= 0 or request.limit > 100:
            request.limit = 20

        queries = []

        if (
            not request.actionable_types
            or ActionableType.CALENDAR_EVENT in request.actionable_types
        ):
            queries.append(self._get_calendar_events_query(request, user_id))
        if (
            not request.actionable_types
            or ActionableType.REMINDER in request.actionable_types
        ):
            queries.append(self._get_reminders_query(request, user_id))
        if (
            not request.actionable_types
            or ActionableType.FOLLOW_UP in request.actionable_types
        ):
            queries.append(self._get_follow_ups_query(request, user_id))
        if (
            not request.actionable_types
            or ActionableType.NOTE in request.actionable_types
        ):
            queries.append(self._get_notes_query(request, user_id))
        if (
            not request.actionable_types
            or ActionableType.BILL in request.actionable_types
        ):
            queries.append(self._get_bills_query(request, user_id))
        if (
            not request.actionable_types
            or ActionableType.COUPON in request.actionable_types
        ):
            queries.append(self._get_coupons_query(request, user_id))

        all_actionables = []
        for query in queries:
            try:
                result = await self.db.execute(query)
                all_actionables.extend(result.scalars().all())
            except Exception as e:
                logger.error(
                    f"Error executing actionables query for user {user_id}: {e}"
                )
                continue

        all_actionables.sort(
            key=lambda x: getattr(x, "created_at", None) or x.created_at, reverse=True
        )

        total_count = len(all_actionables)

        start = (request.page - 1) * request.limit
        end = start + request.limit
        paginated_actionables = all_actionables[start:end]

        response_objects = []
        for item in paginated_actionables:
            try:
                if isinstance(item, CalendarEvent):
                    response_objects.append(CalendarEventResponse.from_orm(item))
                elif isinstance(item, EmailReminder):
                    response_objects.append(EmailReminderResponse.from_orm(item))
                elif isinstance(item, FollowUp):
                    response_objects.append(FollowUpResponse.from_orm(item))
                elif isinstance(item, EmailNote):
                    response_objects.append(EmailNoteResponse.from_orm(item))
                elif isinstance(item, Bill):
                    response_objects.append(BillResponse.from_orm(item))
                elif isinstance(item, Coupon):
                    response_objects.append(CouponResponse.from_orm(item))
            except Exception as e:
                logger.error(
                    f"Error converting actionable to response for user {user_id}: {e}"
                )
                continue

        logger.info(
            f"Retrieved {len(response_objects)} actionables for user {user_id} (total: {total_count})"
        )
        return response_objects, total_count

    def _apply_common_filters(
        self, query, model, request: ActionableListRequest, user_id: int
    ):
        """Apply common filters ensuring proper user isolation."""

        query = query.join(Email).filter(Email.user_id == user_id)

        if request.email_id:
            if request.email_id <= 0:
                logger.warning(
                    f"Invalid email_id provided in filter: {request.email_id}"
                )
                raise ValueError("Invalid email_id")
            query = query.filter(model.email_id == request.email_id)

        if request.thread_id:
            if request.thread_id <= 0:
                logger.warning(
                    f"Invalid thread_id provided in filter: {request.thread_id}"
                )
                raise ValueError("Invalid thread_id")
            query = query.filter(Email.thread_id == request.thread_id)

        date_field = getattr(
            model,
            "start_time",
            getattr(
                model,
                "reminder_time",
                getattr(model, "follow_up_time", getattr(model, "created_at", None)),
            ),
        )

        if date_field and request.start_date:
            try:
                from datetime import datetime

                if isinstance(request.start_date, str):
                    start_date = datetime.fromisoformat(
                        request.start_date.replace("Z", "+00:00")
                    )
                else:
                    start_date = request.start_date
                query = query.filter(date_field >= start_date)
            except (ValueError, TypeError):
                logger.warning(f"Invalid start_date format: {request.start_date}")
                pass

        if date_field and request.end_date:
            try:
                from datetime import datetime

                if isinstance(request.end_date, str):
                    end_date = datetime.fromisoformat(
                        request.end_date.replace("Z", "+00:00")
                    )
                else:
                    end_date = request.end_date
                query = query.filter(date_field <= end_date)
            except (ValueError, TypeError):
                logger.warning(f"Invalid end_date format: {request.end_date}")
                pass

        return query

    def _get_calendar_events_query(self, request: ActionableListRequest, user_id: int):
        query = select(CalendarEvent).options(joinedload(CalendarEvent.attendees))
        return self._apply_common_filters(query, CalendarEvent, request, user_id)

    def _get_reminders_query(self, request: ActionableListRequest, user_id: int):
        query = select(EmailReminder)
        return self._apply_common_filters(query, EmailReminder, request, user_id)

    def _get_follow_ups_query(self, request: ActionableListRequest, user_id: int):
        query = select(FollowUp)
        return self._apply_common_filters(query, FollowUp, request, user_id)

    def _get_notes_query(self, request: ActionableListRequest, user_id: int):
        query = select(EmailNote)
        return self._apply_common_filters(query, EmailNote, request, user_id)

    def _get_bills_query(self, request: ActionableListRequest, user_id: int):
        query = select(Bill)
        return self._apply_common_filters(query, Bill, request, user_id)

    def _get_coupons_query(self, request: ActionableListRequest, user_id: int):
        query = select(Coupon)
        return self._apply_common_filters(query, Coupon, request, user_id)


async def get_actionable_service(db: AsyncSession = Depends(get_async_db)):
    return ActionableService(db)
