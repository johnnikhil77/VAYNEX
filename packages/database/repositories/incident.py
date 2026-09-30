from __future__ import annotations

import uuid

from sqlalchemy import func, select

from packages.common.enums import IncidentStatus, Severity
from packages.database.models import Incident
from packages.database.repositories.base import BaseRepository

ACTIVE_STATUSES = (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING, IncidentStatus.MITIGATING)


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    async def list(
        self,
        *,
        status: IncidentStatus | None = None,
        severity: Severity | None = None,
        active_only: bool = False,
        event_id: uuid.UUID | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Incident], int]:
        stmt = select(Incident)
        if status:
            stmt = stmt.where(Incident.status == status)
        if active_only:
            stmt = stmt.where(Incident.status.in_(ACTIVE_STATUSES))
        if severity:
            stmt = stmt.where(Incident.severity == severity)
        if event_id:
            stmt = stmt.where(Incident.event_id == event_id)
        stmt = stmt.order_by(Incident.detected_at.desc(), Incident.id)
        return await self.paginate(stmt, limit=limit, offset=offset)

    async def get_by_event(self, event_id: uuid.UUID) -> Incident | None:
        return await self.session.scalar(select(Incident).where(Incident.event_id == event_id))

    async def count_active(self, *, severity: Severity | None = None) -> int:
        stmt = select(func.count()).select_from(Incident).where(Incident.status.in_(ACTIVE_STATUSES))
        if severity:
            stmt = stmt.where(Incident.severity == severity)
        return int(await self.session.scalar(stmt) or 0)

    async def recent(self, limit: int = 5) -> list[Incident]:
        stmt = select(Incident).order_by(Incident.detected_at.desc(), Incident.id).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def active_ids(self) -> list[uuid.UUID]:
        stmt = select(Incident.id).where(Incident.status.in_(ACTIVE_STATUSES))
        return list((await self.session.scalars(stmt)).all())
