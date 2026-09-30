from __future__ import annotations

from sqlalchemy import select

from packages.database.models import Organization
from packages.database.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_name(self, name: str) -> Organization | None:
        return await self.session.scalar(select(Organization).where(Organization.name == name))

    async def list(self, *, limit: int, offset: int) -> tuple[list[Organization], int]:
        return await self.paginate(select(Organization).order_by(Organization.name), limit=limit, offset=offset)
