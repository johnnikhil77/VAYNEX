from __future__ import annotations

import uuid

from sqlalchemy import func, select

from packages.common.enums import Criticality, ServiceStatus, ServiceType
from packages.database.models import PublicService
from packages.database.repositories.base import BaseRepository


class ServiceRepository(BaseRepository[PublicService]):
    model = PublicService

    async def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        service_type: ServiceType | None = None,
        status: ServiceStatus | None = None,
        criticality: Criticality | None = None,
        infrastructure_id: uuid.UUID | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[PublicService], int]:
        stmt = select(PublicService)
        if organization_id:
            stmt = stmt.where(PublicService.organization_id == organization_id)
        if service_type:
            stmt = stmt.where(PublicService.service_type == service_type)
        if status:
            stmt = stmt.where(PublicService.status == status)
        if criticality:
            stmt = stmt.where(PublicService.criticality == criticality)
        if infrastructure_id:
            stmt = stmt.where(PublicService.infrastructure_id == infrastructure_id)
        stmt = stmt.order_by(PublicService.name, PublicService.id)
        return await self.paginate(stmt, limit=limit, offset=offset)

    async def all(self) -> list[PublicService]:
        return list((await self.session.scalars(select(PublicService))).all())

    async def get_by_name(self, name: str) -> PublicService | None:
        return await self.session.scalar(
            select(PublicService).where(PublicService.name == name).order_by(PublicService.created_at)
        )

    async def count(self) -> int:
        return int(await self.session.scalar(select(func.count()).select_from(PublicService)) or 0)

    async def count_by_status(self) -> dict[str, int]:
        rows = await self.session.execute(select(PublicService.status, func.count()).group_by(PublicService.status))
        return {str(status): int(count) for status, count in rows.all()}
