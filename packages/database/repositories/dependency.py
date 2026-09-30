from __future__ import annotations

import uuid

from sqlalchemy import or_, select

from packages.common.enums import DependencyStrength, DependencyType
from packages.database.models import Dependency
from packages.database.repositories.base import BaseRepository


class DependencyRepository(BaseRepository[Dependency]):
    model = Dependency

    async def list(
        self,
        *,
        infrastructure_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None,
        dependency_type: DependencyType | None = None,
        strength: DependencyStrength | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Dependency], int]:
        stmt = select(Dependency)
        if infrastructure_id:
            stmt = stmt.where(
                or_(
                    Dependency.source_infrastructure_id == infrastructure_id,
                    Dependency.target_infrastructure_id == infrastructure_id,
                )
            )
        if service_id:
            stmt = stmt.where(
                or_(Dependency.source_service_id == service_id, Dependency.target_service_id == service_id)
            )
        if dependency_type:
            stmt = stmt.where(Dependency.dependency_type == dependency_type)
        if strength:
            stmt = stmt.where(Dependency.strength == strength)
        stmt = stmt.order_by(Dependency.created_at, Dependency.id)
        return await self.paginate(stmt, limit=limit, offset=offset)

    async def all(self) -> list[Dependency]:
        stmt = select(Dependency).order_by(Dependency.created_at, Dependency.id)
        return list((await self.session.scalars(stmt)).all())

    async def find_duplicate(
        self,
        *,
        source_infrastructure_id: uuid.UUID | None,
        source_service_id: uuid.UUID | None,
        target_infrastructure_id: uuid.UUID | None,
        target_service_id: uuid.UUID | None,
        dependency_type: DependencyType,
    ) -> Dependency | None:
        def _eq(column, value):  # type: ignore[no-untyped-def]
            return column.is_(None) if value is None else column == value

        stmt = select(Dependency).where(
            _eq(Dependency.source_infrastructure_id, source_infrastructure_id),
            _eq(Dependency.source_service_id, source_service_id),
            _eq(Dependency.target_infrastructure_id, target_infrastructure_id),
            _eq(Dependency.target_service_id, target_service_id),
            Dependency.dependency_type == dependency_type,
        )
        return await self.session.scalar(stmt)
