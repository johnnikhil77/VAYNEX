from __future__ import annotations

from fastapi import APIRouter, Request

from apps.api.api.v1._common import CacheDep
from apps.api.dependencies.auth import DbSession, ViewerUser
from apps.api.schemas.dashboard import DashboardOverview
from apps.api.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def overview(request: Request, session: DbSession, cache: CacheDep, _: ViewerUser) -> DashboardOverview:
    ttl = request.app.state.settings.DASHBOARD_CACHE_TTL_SECONDS
    return await DashboardService(session, cache, ttl).overview()
