from __future__ import annotations

import uuid

from fastapi import APIRouter

from apps.api.api.v1._common import CacheDep, PageParams
from apps.api.dependencies.auth import DbSession, OperatorUser, ViewerUser
from apps.api.schemas.common import Page
from apps.api.schemas.recommendation import RecommendationResponse, RecommendationUpdate
from apps.api.services.recommendation_service import RecommendationService
from packages.common.enums import RecommendationPriority, RecommendationSource, RecommendationStatus

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=Page[RecommendationResponse])
async def list_recommendations(
    session: DbSession,
    _: ViewerUser,
    page: PageParams,
    incident_id: uuid.UUID | None = None,
    status: RecommendationStatus | None = None,
    source: RecommendationSource | None = None,
    priority: RecommendationPriority | None = None,
) -> Page[RecommendationResponse]:
    return await RecommendationService(session).list(
        incident_id=incident_id,
        status=status,
        source=source,
        priority=priority,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(recommendation_id: uuid.UUID, session: DbSession, _: ViewerUser) -> RecommendationResponse:
    return await RecommendationService(session).get(recommendation_id)


@router.patch(
    "/{recommendation_id}",
    response_model=RecommendationResponse,
    summary="Operator decision: ACCEPTED, REJECTED or COMPLETED",
)
async def decide_recommendation(
    recommendation_id: uuid.UUID, data: RecommendationUpdate, session: DbSession, cache: CacheDep, user: OperatorUser
) -> RecommendationResponse:
    return await RecommendationService(session, cache).decide(recommendation_id, data, user)
