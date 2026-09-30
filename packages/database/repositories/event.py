from __future__ import annotations

import uuid

from sqlalchemy import select

from packages.common.enums import EventType, Severity
from packages.database.models import Event
from packages.database.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    async def list(
        self,
        *,
        event_type: EventType | None = None,
        severity: Severity | None = None,
        infrastructure_id: uuid.UUID | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Event], int]:
        stmt = select(Event)
        if event_type:
            stmt = stmt.where(Event.event_type == event_type)
        if severity:
            stmt = stmt.where(Event.severity == severity)
        if infrastructure_id:
            stmt = stmt.where(Event.infrastructure_id == infrastructure_id)
        stmt = stmt.order_by(Event.occurred_at.desc(), Event.id)
        return await self.paginate(stmt, limit=limit, offset=offset)

    async def recent(self, limit: int = 5) -> list[Event]:
        stmt = select(Event).order_by(Event.created_at.desc(), Event.id).limit(limit)
        return list((await self.session.scalars(stmt)).all())
