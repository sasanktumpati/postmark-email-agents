from datetime import datetime
from typing import Tuple

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.db import get_async_db
from app.core.logger import get_logger
from app.modules.actionables.api import (
    ActionableListRequest,
    ActionableType,
    BillResponse,
    CalendarActionables,
    CalendarEventResponse,
    CouponResponse,
    EmailNoteResponse,
    EmailReminderResponse,
    FollowUpResponse,
    GroupedActionablesResponse,
    NotesActionables,
    ShoppingActionables,
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
    ) -> Tuple[GroupedActionablesResponse, int]:
        logger.debug(f"Listing actionables for user ID: {user_id}")

        if user_id <= 0:
            logger.error(f"Invalid user_id provided: {user_id}")
            raise ValueError("Invalid user_id")

        if request.page <= 0:
            request.page = 1
        if request.limit <= 0 or request.limit > 100:
            request.limit = 20

        calendar_events = []
        calendar_reminders = []
        calendar_follow_ups = []
        notes = []
        shopping_bills = []
        shopping_coupons = []

        if (
            not request.actionable_types
            or ActionableType.CALENDAR_EVENT in request.actionable_types
        ):
            events_query = self._get_calendar_events_query(request, user_id)
            try:
                result = await self.db.execute(events_query)
                events = result.scalars().all()
                calendar_events = [
                    CalendarEventResponse.model_validate(event) for event in events
                ]
            except Exception as e:
                logger.error(f"Error fetching calendar events for user {user_id}: {e}")

        if (
            not request.actionable_types
            or ActionableType.REMINDER in request.actionable_types
        ):
            reminders_query = self._get_reminders_query(request, user_id)
            try:
                result = await self.db.execute(reminders_query)
                reminders = result.scalars().all()
                calendar_reminders = [
                    EmailReminderResponse.model_validate(reminder)
                    for reminder in reminders
                ]
            except Exception as e:
                logger.error(f"Error fetching reminders for user {user_id}: {e}")

        if (
            not request.actionable_types
            or ActionableType.FOLLOW_UP in request.actionable_types
        ):
            follow_ups_query = self._get_follow_ups_query(request, user_id)
            try:
                result = await self.db.execute(follow_ups_query)
                follow_ups = result.scalars().all()
                calendar_follow_ups = [
                    FollowUpResponse.model_validate(follow_up)
                    for follow_up in follow_ups
                ]
            except Exception as e:
                logger.error(f"Error fetching follow ups for user {user_id}: {e}")

        if (
            not request.actionable_types
            or ActionableType.NOTE in request.actionable_types
        ):
            notes_query = self._get_notes_query(request, user_id)
            try:
                result = await self.db.execute(notes_query)
                notes_data = result.scalars().all()
                notes = [EmailNoteResponse.model_validate(note) for note in notes_data]
            except Exception as e:
                logger.error(f"Error fetching notes for user {user_id}: {e}")

        if (
            not request.actionable_types
            or ActionableType.BILL in request.actionable_types
        ):
            bills_query = self._get_bills_query(request, user_id)
            try:
                result = await self.db.execute(bills_query)
                bills = result.scalars().all()
                shopping_bills = [BillResponse.model_validate(bill) for bill in bills]
            except Exception as e:
                logger.error(f"Error fetching bills for user {user_id}: {e}")

        if (
            not request.actionable_types
            or ActionableType.COUPON in request.actionable_types
        ):
            coupons_query = self._get_coupons_query(request, user_id)
            try:
                result = await self.db.execute(coupons_query)
                coupons = result.scalars().all()
                shopping_coupons = [
                    CouponResponse.model_validate(coupon) for coupon in coupons
                ]
            except Exception as e:
                logger.error(f"Error fetching coupons for user {user_id}: {e}")

        total_count = (
            len(calendar_events)
            + len(calendar_reminders)
            + len(calendar_follow_ups)
            + len(notes)
            + len(shopping_bills)
            + len(shopping_coupons)
        )

        start = (request.page - 1) * request.limit
        end = start + request.limit

        all_items = []
        all_items.extend([("event", item) for item in calendar_events])
        all_items.extend([("reminder", item) for item in calendar_reminders])
        all_items.extend([("follow_up", item) for item in calendar_follow_ups])
        all_items.extend([("note", item) for item in notes])
        all_items.extend([("bill", item) for item in shopping_bills])
        all_items.extend([("coupon", item) for item in shopping_coupons])

        try:

            def get_sort_key(item):
                """Get sorting key for actionable item, defaulting to epoch for None dates."""
                _, obj = item
                date_value = (
                    getattr(obj, "created_at", None)
                    or getattr(obj, "start_time", None)
                    or getattr(obj, "reminder_time", None)
                    or getattr(obj, "follow_up_time", None)
                )

                return date_value or datetime(2025, 1, 1)

            all_items.sort(key=get_sort_key, reverse=True)
        except Exception as e:
            logger.warning(f"Could not sort actionables by date: {e}")

        paginated_items = all_items[start:end]

        paginated_events = []
        paginated_reminders = []
        paginated_follow_ups = []
        paginated_notes = []
        paginated_bills = []
        paginated_coupons = []

        for item_type, item in paginated_items:
            if item_type == "event":
                paginated_events.append(item)
            elif item_type == "reminder":
                paginated_reminders.append(item)
            elif item_type == "follow_up":
                paginated_follow_ups.append(item)
            elif item_type == "note":
                paginated_notes.append(item)
            elif item_type == "bill":
                paginated_bills.append(item)
            elif item_type == "coupon":
                paginated_coupons.append(item)

        grouped_response = GroupedActionablesResponse(
            calendar=CalendarActionables(
                events=paginated_events,
                reminders=paginated_reminders,
                follow_ups=paginated_follow_ups,
            ),
            notes=NotesActionables(notes=paginated_notes),
            shopping=ShoppingActionables(
                bills=paginated_bills, coupons=paginated_coupons
            ),
            total_count=total_count,
        )

        logger.info(
            f"Retrieved grouped actionables for user {user_id} "
            f"(events: {len(paginated_events)}, reminders: {len(paginated_reminders)}, "
            f"follow_ups: {len(paginated_follow_ups)}, notes: {len(paginated_notes)}, "
            f"bills: {len(paginated_bills)}, coupons: {len(paginated_coupons)}, total: {total_count})"
        )

        return grouped_response, total_count

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
