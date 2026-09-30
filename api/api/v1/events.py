from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from apps.api.api.v1._common import AIProviderDep, CacheDep, PageParams
from apps.api.dependencies.auth import DbSession, OperatorUser, ViewerUser
from apps.api.schemas.common import Page
from apps.api.schemas.event import EventCreate, EventProcessingResult, EventResponse
from apps.api.services.event_service import EventService
from packages.common.enums import EventType, Severity

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "",
    response_model=EventProcessingResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest an event and run the full intelligence pipeline",
)
async def ingest_event(
    data: EventCreate, session: DbSession, cache: CacheDep, ai: AIProviderDep, user: OperatorUser
) -> EventProcessingResult:
    return await EventService(session, ai, cache).ingest(data, user)


@router.get("", response_model=Page[EventResponse])
async def list_events(
    session: DbSession,
    ai: AIProviderDep,
    _: ViewerUser,
    page: PageParams,
    event_type: EventType | None = None,
    severity: Severity | None = None,
    infrastructure_id: uuid.UUID | None = None,
) -> Page[EventResponse]:
    return await EventService(session, ai).list(
        event_type=event_type,
        severity=severity,
        infrastructure_id=infrastructure_id,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: uuid.UUID, session: DbSession, ai: AIProviderDep, _: ViewerUser) -> EventResponse:
    return await EventService(session, ai).get(event_id)
