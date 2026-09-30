from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from apps.api.api.v1._common import CacheDep, PageParams
from apps.api.dependencies.auth import DbSession, OperatorUser, ViewerUser
from apps.api.schemas.common import Page
from apps.api.schemas.incident import (
    IncidentDetailResponse,
    IncidentResolveRequest,
    IncidentResponse,
    IncidentUpdate,
)
from apps.api.services.incident_service import IncidentService
from packages.common.enums import IncidentStatus, Severity

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=Page[IncidentResponse])
async def list_incidents(
    session: DbSession,
    _: ViewerUser,
    page: PageParams,
    status_: Annotated[IncidentStatus | None, Query(alias="status")] = None,
    severity: Severity | None = None,
    active_only: bool = False,
) -> Page[IncidentResponse]:
    return await IncidentService(session).list(
        status=status_, severity=severity, active_only=active_only, limit=page.limit, offset=page.offset
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentDetailResponse,
    summary="Incident with event, impact, risk, AI analysis and recommendations",
)
async def get_incident(incident_id: uuid.UUID, session: DbSession, _: ViewerUser) -> IncidentDetailResponse:
    return await IncidentService(session).detail(incident_id)


@router.patch("/{incident_id}", response_model=IncidentDetailResponse)
async def update_incident(
    incident_id: uuid.UUID, data: IncidentUpdate, session: DbSession, cache: CacheDep, user: OperatorUser
) -> IncidentDetailResponse:
    return await IncidentService(session, cache).update(incident_id, data, user)


@router.post("/{incident_id}/resolve", response_model=IncidentDetailResponse)
async def resolve_incident(
    incident_id: uuid.UUID,
    session: DbSession,
    cache: CacheDep,
    user: OperatorUser,
    data: IncidentResolveRequest | None = None,
) -> IncidentDetailResponse:
    return await IncidentService(session, cache).resolve(incident_id, data or IncidentResolveRequest(), user)
