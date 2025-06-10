from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func, select

from app.core.logger import get_logger

from .database import Base

ModelType = TypeVar("ModelType", bound=Base)
logger = get_logger(__name__)


class Repository(Generic[ModelType]):
    """
    Generic repository class with proper transaction management.
    """

    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class
        self.logger = get_logger(f"{__name__}.{self.model_class.__name__}")

    async def create(self, session: AsyncSession, obj: ModelType) -> ModelType:
        """Create a new object in the database."""
        self.logger.debug(f"Creating new {self.model_class.__name__} object.")
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        self.logger.info(
            f"Successfully created {self.model_class.__name__} with id {obj.id}."
        )
        return obj

    async def create_many(
        self, session: AsyncSession, objects: List[ModelType]
    ) -> List[ModelType]:
        """Create multiple objects in a single transaction."""
        if not objects:
            self.logger.warning(
                f"No {self.model_class.__name__} objects provided for bulk creation."
            )
            return []

        self.logger.debug(
            f"Creating {len(objects)} new {self.model_class.__name__} objects."
        )
        session.add_all(objects)
        await session.flush()
        for obj in objects:
            await session.refresh(obj)
        self.logger.info(
            f"Successfully created {len(objects)} {self.model_class.__name__} objects."
        )
        return objects

    async def get_by_id(
        self, session: AsyncSession, obj_id: int
    ) -> Optional[ModelType]:
        """Get object by ID."""
        if obj_id <= 0:
            self.logger.warning(
                f"Invalid ID provided for {self.model_class.__name__}: {obj_id}"
            )
            return None

        query = select(self.model_class).where(self.model_class.id == obj_id)
        result = await session.execute(query)
        obj = result.scalar_one_or_none()

        if obj:
            self.logger.debug(f"{self.model_class.__name__} with id {obj_id} found.")
        else:
            self.logger.debug(
                f"{self.model_class.__name__} with id {obj_id} not found."
            )

        return obj

    async def update(self, session: AsyncSession, obj: ModelType) -> ModelType:
        """Update an existing object."""
        self.logger.debug(f"Updating {self.model_class.__name__} with id {obj.id}.")
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        self.logger.info(
            f"Successfully updated {self.model_class.__name__} with id {obj.id}."
        )
        return obj

    async def delete(self, session: AsyncSession, obj: ModelType) -> bool:
        """Delete an object."""
        self.logger.debug(f"Deleting {self.model_class.__name__} with id {obj.id}.")
        await session.delete(obj)
        await session.flush()
        self.logger.info(
            f"Successfully deleted {self.model_class.__name__} with id {obj.id}."
        )
        return True

    async def count(self, session: AsyncSession, **filters) -> int:
        """Count objects with optional filters."""
        query = select(func.count(self.model_class.id))
        if filters:
            conditions = self._build_filter_conditions(filters)
            if conditions:
                query = query.where(and_(*conditions))
        result = await session.execute(query)
        count = result.scalar() or 0
        self.logger.debug(
            f"Counted {count} {self.model_class.__name__} objects with filters: {filters}"
        )
        return count

    async def exists(self, session: AsyncSession, **filters) -> bool:
        """Check if objects exist with optional filters."""
        count = await self.count(session, **filters)
        return count > 0

    async def list_all(
        self,
        session: AsyncSession,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = True,
        **filters,
    ) -> List[ModelType]:
        """List objects with pagination and filtering."""
        self.logger.debug(
            f"Listing {self.model_class.__name__} objects with offset={offset}, limit={limit}"
        )

        query = select(self.model_class)

        if filters:
            conditions = self._build_filter_conditions(filters)
            if conditions:
                query = query.where(and_(*conditions))

        if order_by and hasattr(self.model_class, order_by):
            order_column = getattr(self.model_class, order_by)
            if order_desc:
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))

        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        objects = list(result.scalars().all())
        self.logger.info(
            f"Retrieved {len(objects)} {self.model_class.__name__} objects."
        )
        return objects

    def _build_filter_conditions(self, filters: Dict[str, Any]) -> List:
        """Build filter conditions from a dictionary of filters."""
        conditions = []
        for key, value in filters.items():
            if hasattr(self.model_class, key) and value is not None:
                column = getattr(self.model_class, key)
                if isinstance(value, list):
                    conditions.append(column.in_(value))
                elif isinstance(value, str) and key.endswith("_like"):
                    actual_key = key.replace("_like", "")
                    if hasattr(self.model_class, actual_key):
                        actual_column = getattr(self.model_class, actual_key)
                        conditions.append(actual_column.ilike(f"%{value}%"))
                else:
                    conditions.append(column == value)
        return conditions

    async def flush(self) -> None:
        """Flush pending changes without committing."""
        await self.db.flush()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.db.rollback()


class TransactionalRepository(Repository[ModelType]):
    """Repository that batches operations and commits only when explicitly requested."""

    async def create(
        self, session: AsyncSession, obj: ModelType, commit: bool = False
    ) -> ModelType:
        """Create a new object (batched by default)."""
        return await super().create(session, obj)

    async def create_many(
        self, session: AsyncSession, objects: List[ModelType], commit: bool = False
    ) -> List[ModelType]:
        """Create multiple objects (batched by default)."""
        return await super().create_many(session, objects)

    async def update(
        self, session: AsyncSession, obj: ModelType, commit: bool = False
    ) -> ModelType:
        """Update an existing object (batched by default)."""
        return await super().update(session, obj)

    async def delete(
        self, session: AsyncSession, obj: ModelType, commit: bool = False
    ) -> bool:
        """Delete an object (batched by default)."""
        return await super().delete(session, obj)
