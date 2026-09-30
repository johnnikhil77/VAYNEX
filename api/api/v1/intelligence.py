from __future__ import annotations

import uuid

from fastapi import APIRouter

from apps.api.api.v1._common import AIProviderDep
from apps.api.dependencies.auth import DbSession, OperatorUser, ViewerUser
from apps.api.schemas.intelligence import AnalyzeIncidentResponse, ProviderInfoResponse
from apps.api.services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence"])


@router.post(
    "/analyze/{incident_id}",
    response_model=AnalyzeIncidentResponse,
    summary="Run AI analysis for an incident (advisory only)",
)
async def analyze_incident(
    incident_id: uuid.UUID, session: DbSession, ai: AIProviderDep, user: OperatorUser
) -> AnalyzeIncidentResponse:
    return await IntelligenceService(session, ai).analyze_incident(incident_id, user)


@router.get("/provider", response_model=ProviderInfoResponse, summary="Active AI provider")
async def provider(session: DbSession, ai: AIProviderDep, _: ViewerUser) -> ProviderInfoResponse:
    return IntelligenceService(session, ai).provider_info()
