from abc import ABC
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func, select

from .database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType], ABC):
    """Base repository class with proper transaction management."""

    def __init__(self, db_session: AsyncSession, model_class: Type[ModelType]):
        self.db = db_session
        self.model_class = model_class

    async def create(self, obj: ModelType, commit: bool = True) -> ModelType:
        """Create a new object in the database."""
        self.db.add(obj)
        if commit:
            await self.db.commit()
            await self.db.refresh(obj)
        return obj

    async def create_many(
        self, objects: List[ModelType], commit: bool = True
    ) -> List[ModelType]:
        """Create multiple objects in a single transaction."""
        self.db.add_all(objects)
        if commit:
            await self.db.commit()
            for obj in objects:
                await self.db.refresh(obj)
        return objects

    async def get_by_id(self, obj_id: int) -> Optional[ModelType]:
        """Get object by ID."""
        query = select(self.model_class).where(self.model_class.id == obj_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update(self, obj: ModelType, commit: bool = True) -> ModelType:
        """Update an existing object."""
        if commit:
            await self.db.commit()
            await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType, commit: bool = True) -> bool:
        """Delete an object."""
        await self.db.delete(obj)
        if commit:
            await self.db.commit()
        return True

    async def count(self, **filters) -> int:
        """Count objects with optional filters."""
        query = select(func.count(self.model_class.id))
        if filters:
            conditions = self._build_filter_conditions(filters)
            if conditions:
                query = query.where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(self, **filters) -> bool:
        """Check if objects exist with optional filters."""
        count = await self.count(**filters)
        return count > 0

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = True,
        **filters,
    ) -> List[ModelType]:
        """List objects with pagination and filtering."""
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

        result = await self.db.execute(query)
        return list(result.scalars().all())

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


class TransactionalRepository(BaseRepository[ModelType]):
    """Repository that batches operations and commits only when explicitly requested."""

    def __init__(self, db_session: AsyncSession, model_class: Type[ModelType]):
        super().__init__(db_session, model_class)

    async def create(self, obj: ModelType, commit: bool = False) -> ModelType:
        """Create a new object (batched by default)."""
        return await super().create(obj, commit=commit)

    async def create_many(
        self, objects: List[ModelType], commit: bool = False
    ) -> List[ModelType]:
        """Create multiple objects (batched by default)."""
        return await super().create_many(objects, commit=commit)

    async def update(self, obj: ModelType, commit: bool = False) -> ModelType:
        """Update an existing object (batched by default)."""
        return await super().update(obj, commit=commit)

    async def delete(self, obj: ModelType, commit: bool = False) -> bool:
        """Delete an object (batched by default)."""
        return await super().delete(obj, commit=commit)
