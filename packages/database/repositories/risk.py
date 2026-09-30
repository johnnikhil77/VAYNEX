from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from packages.database.models import RiskAssessment
from packages.database.repositories.base import BaseRepository


class RiskRepository(BaseRepository[RiskAssessment]):
    model = RiskAssessment

    async def latest_for_incident(self, incident_id: uuid.UUID) -> RiskAssessment | None:
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.incident_id == incident_id)
            .order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def history_for_incident(self, incident_id: uuid.UUID) -> list[RiskAssessment]:
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.incident_id == incident_id)
            .order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def latest_for_incidents(self, incident_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, RiskAssessment]:
        """Latest risk per incident (DISTINCT ON)."""
        if not incident_ids:
            return {}
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.incident_id.in_(list(incident_ids)))
            .distinct(RiskAssessment.incident_id)
            .order_by(RiskAssessment.incident_id, RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
        )
        rows = (await self.session.scalars(stmt)).all()
        return {r.incident_id: r for r in rows}

    async def average_score(self, incident_ids: Sequence[uuid.UUID]) -> float | None:
        latest = await self.latest_for_incidents(incident_ids)
        if not latest:
            return None
        return sum(r.score for r in latest.values()) / len(latest)

    async def count_all(self) -> int:
        return int(await self.session.scalar(select(func.count()).select_from(RiskAssessment)) or 0)
