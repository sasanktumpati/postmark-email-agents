from typing import List, Tuple

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.db import get_async_db
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


class ActionableService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def list_actionables(
        self, request: ActionableListRequest
    ) -> Tuple[List[ActionableObject], int]:
        queries = []

        if (
            not request.actionable_types
            or ActionableType.CALENDAR_EVENT in request.actionable_types
        ):
            queries.append(self._get_calendar_events_query(request))
        if (
            not request.actionable_types
            or ActionableType.REMINDER in request.actionable_types
        ):
            queries.append(self._get_reminders_query(request))
        if (
            not request.actionable_types
            or ActionableType.FOLLOW_UP in request.actionable_types
        ):
            queries.append(self._get_follow_ups_query(request))
        if (
            not request.actionable_types
            or ActionableType.NOTE in request.actionable_types
        ):
            queries.append(self._get_notes_query(request))
        if (
            not request.actionable_types
            or ActionableType.BILL in request.actionable_types
        ):
            queries.append(self._get_bills_query(request))
        if (
            not request.actionable_types
            or ActionableType.COUPON in request.actionable_types
        ):
            queries.append(self._get_coupons_query(request))

        all_actionables = []
        for query in queries:
            result = await self.db.execute(query)
            all_actionables.extend(result.scalars().all())

        all_actionables.sort(key=lambda x: x.created_at, reverse=True)

        total_count = len(all_actionables)

        start = (request.page - 1) * request.limit
        end = start + request.limit
        paginated_actionables = all_actionables[start:end]

        response_objects = []
        for item in paginated_actionables:
            if isinstance(item, CalendarEvent):
                response_objects.append(CalendarEventResponse.from_attributes(item))
            elif isinstance(item, EmailReminder):
                response_objects.append(EmailReminderResponse.from_attributes(item))
            elif isinstance(item, FollowUp):
                response_objects.append(FollowUpResponse.from_attributes(item))
            elif isinstance(item, EmailNote):
                response_objects.append(EmailNoteResponse.from_attributes(item))
            elif isinstance(item, Bill):
                response_objects.append(BillResponse.from_attributes(item))
            elif isinstance(item, Coupon):
                response_objects.append(CouponResponse.from_attributes(item))

        return response_objects, total_count

    def _apply_common_filters(self, query, model, request: ActionableListRequest):
        if request.email_id:
            query = query.filter(model.email_id == request.email_id)
        if request.thread_id:
            query = query.join(Email).filter(Email.thread_id == request.thread_id)

        date_field = getattr(
            model,
            "start_time",
            getattr(
                model,
                "reminder_time",
                getattr(model, "follow_up_time", getattr(model, "created_at", None)),
            ),
        )

        if date_field:
            if request.start_date:
                query = query.filter(date_field >= request.start_date)
            if request.end_date:
                query = query.filter(date_field <= request.end_date)

        return query

    def _get_calendar_events_query(self, request: ActionableListRequest):
        query = select(CalendarEvent).options(joinedload(CalendarEvent.attendees))
        return self._apply_common_filters(query, CalendarEvent, request)

    def _get_reminders_query(self, request: ActionableListRequest):
        query = select(EmailReminder)
        return self._apply_common_filters(query, EmailReminder, request)

    def _get_follow_ups_query(self, request: ActionableListRequest):
        query = select(FollowUp)
        return self._apply_common_filters(query, FollowUp, request)

    def _get_notes_query(self, request: ActionableListRequest):
        query = select(EmailNote)
        return self._apply_common_filters(query, EmailNote, request)

    def _get_bills_query(self, request: ActionableListRequest):
        query = select(Bill)
        return self._apply_common_filters(query, Bill, request)

    def _get_coupons_query(self, request: ActionableListRequest):
        query = select(Coupon)
        return self._apply_common_filters(query, Coupon, request)


async def get_actionable_service(db: AsyncSession = Depends(get_async_db)):
    return ActionableService(db)
