from __future__ import annotations

import uuid

from fastapi import APIRouter

from apps.api.dependencies.auth import DbSession, OperatorUser, ViewerUser
from apps.api.schemas.risk import RiskEvaluateRequest, RiskEvaluateResponse, RiskHistoryResponse, RiskResponse
from apps.api.services.risk_service import RiskService

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get(
    "/incidents/{incident_id}",
    response_model=RiskHistoryResponse,
    summary="Latest risk assessment and history for an incident",
)
async def incident_risk(incident_id: uuid.UUID, session: DbSession, _: ViewerUser) -> RiskHistoryResponse:
    return await RiskService(session).history(incident_id)


@router.post(
    "/incidents/{incident_id}/recalculate",
    response_model=RiskResponse,
    summary="Recalculate risk from the stored impact snapshot",
)
async def recalculate_risk(incident_id: uuid.UUID, session: DbSession, user: OperatorUser) -> RiskResponse:
    return await RiskService(session).recalculate(incident_id, user)


@router.post(
    "/evaluate", response_model=RiskEvaluateResponse, summary="Stateless what-if risk evaluation (nothing is stored)"
)
async def evaluate_risk(data: RiskEvaluateRequest, session: DbSession, _: ViewerUser) -> RiskEvaluateResponse:
    return RiskService(session).evaluate(data)
