from __future__ import annotations

import logging
import uuid
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import case, cast, func, select
from sqlalchemy.exc import DBAPIError

from packages.common.enums import Criticality, InfrastructureStatus, InfrastructureType
from packages.common.utils import haversine_m
from packages.database.models import Infrastructure
from packages.database.repositories.base import BaseRepository

logger = logging.getLogger("vaynex.repositories.infrastructure")


class InfrastructureRepository(BaseRepository[Infrastructure]):
    model = Infrastructure

    async def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        infrastructure_type: InfrastructureType | None = None,
        status: InfrastructureStatus | None = None,
        criticality: Criticality | None = None,
        search: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Infrastructure], int]:
        stmt = select(Infrastructure)
        if organization_id:
            stmt = stmt.where(Infrastructure.organization_id == organization_id)
        if infrastructure_type:
            stmt = stmt.where(Infrastructure.infrastructure_type == infrastructure_type)
        if status:
            stmt = stmt.where(Infrastructure.status == status)
        if criticality:
            stmt = stmt.where(Infrastructure.criticality == criticality)
        if search:
            stmt = stmt.where(Infrastructure.name.ilike(f"%{search}%"))
        stmt = stmt.order_by(Infrastructure.name, Infrastructure.id)
        return await self.paginate(stmt, limit=limit, offset=offset)

    async def all(self) -> list[Infrastructure]:
        return list((await self.session.scalars(select(Infrastructure))).all())

    async def get_by_name(self, name: str) -> Infrastructure | None:
        return await self.session.scalar(
            select(Infrastructure).where(Infrastructure.name == name).order_by(Infrastructure.created_at)
        )

    async def find_within_radius(
        self, *, latitude: float, longitude: float, radius_m: float
    ) -> list[tuple[Infrastructure, float]]:
        """Assets within ``radius_m`` metres of a point, nearest first.

        Uses PostGIS ``ST_DWithin`` on geography; if PostGIS functions are not
        available it falls back to an in-process haversine scan.
        """
        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        geography = Geography(geometry_type="GEOMETRY", srid=4326)
        geo_loc = cast(Infrastructure.location, geography)
        geo_pt = cast(point, geography)
        distance = func.ST_Distance(geo_loc, geo_pt).label("distance_m")
        stmt: Any = (
            select(Infrastructure, distance)
            .where(Infrastructure.location.is_not(None))
            .where(func.ST_DWithin(geo_loc, geo_pt, radius_m))
            .order_by(distance)
        )
        try:
            async with self.session.begin_nested():
                rows = (await self.session.execute(stmt)).all()
            return [(row[0], float(row[1])) for row in rows]
        except DBAPIError:
            logger.warning("PostGIS spatial query unavailable; using haversine fallback")

        results: list[tuple[Infrastructure, float]] = []
        for item in await self.all():
            if item.latitude is None or item.longitude is None:
                continue
            dist = haversine_m(latitude, longitude, item.latitude, item.longitude)
            if dist <= radius_m:
                results.append((item, dist))
        return sorted(results, key=lambda r: (r[1], r[0].name))

    async def count_by_status(self) -> dict[str, int]:
        rows = await self.session.execute(select(Infrastructure.status, func.count()).group_by(Infrastructure.status))
        return {str(status): int(count) for status, count in rows.all()}

    async def list_critical(self, limit: int = 10) -> list[Infrastructure]:
        stmt = (
            select(Infrastructure)
            .where(Infrastructure.criticality == Criticality.CRITICAL)
            .order_by(
                case(
                    {"FAILED": 0, "DEGRADED": 1, "MAINTENANCE": 2, "OPERATIONAL": 3},
                    value=Infrastructure.status,
                    else_=4,
                ),
                Infrastructure.name,
            )
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())
