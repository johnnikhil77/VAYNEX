from __future__ import annotations

import uuid

from sqlalchemy import case, func, select

from packages.common.enums import RecommendationPriority, RecommendationSource, RecommendationStatus
from packages.database.models import Recommendation
from packages.database.repositories.base import BaseRepository

_PRIORITY_ORDER = case(
    {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3},
    value=Recommendation.priority,
    else_=4,
)


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    async def list(
        self,
        *,
        incident_id: uuid.UUID | None = None,
        status: RecommendationStatus | None = None,
        source: RecommendationSource | None = None,
        priority: RecommendationPriority | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Recommendation], int]:
        stmt = select(Recommendation)
        if incident_id:
            stmt = stmt.where(Recommendation.incident_id == incident_id)
        if status:
            stmt = stmt.where(Recommendation.status == status)
        if source:
            stmt = stmt.where(Recommendation.source == source)
        if priority:
            stmt = stmt.where(Recommendation.priority == priority)
        stmt = stmt.order_by(Recommendation.created_at.desc(), _PRIORITY_ORDER, Recommendation.id)
        return await self.paginate(stmt, limit=limit, offset=offset)

    async def for_incident(self, incident_id: uuid.UUID) -> list[Recommendation]:
        stmt = (
            select(Recommendation)
            .where(Recommendation.incident_id == incident_id)
            .order_by(_PRIORITY_ORDER, Recommendation.source.desc(), Recommendation.created_at, Recommendation.title)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_by_status(self, status: RecommendationStatus) -> int:
        stmt = select(func.count()).select_from(Recommendation).where(Recommendation.status == status)
        return int(await self.session.scalar(stmt) or 0)
