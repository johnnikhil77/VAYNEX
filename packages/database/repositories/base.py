"""Generic async repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def get_many(self, ids: Sequence[uuid.UUID]) -> list[ModelT]:
        if not ids:
            return []
        stmt = select(self.model).where(self.model.id.in_(list(ids)))  # type: ignore[attr-defined]
        return list((await self.session.scalars(stmt)).all())

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

    async def create(self, **values: Any) -> ModelT:
        entity = self.model(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def paginate(self, stmt: Select[Any], *, limit: int, offset: int) -> tuple[list[ModelT], int]:
        total = await self.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
        rows = (await self.session.scalars(stmt.limit(limit).offset(offset))).all()
        return list(rows), int(total or 0)
