from __future__ import annotations

import uuid

from fastapi import APIRouter

from apps.api.api.v1._common import PageParams
from apps.api.dependencies.auth import DbSession, OperatorUser
from apps.api.schemas.audit import AuditLogResponse
from apps.api.schemas.common import Page
from apps.api.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=Page[AuditLogResponse], summary="Audit trail (OPERATOR or ADMIN)")
async def list_audit(
    session: DbSession,
    _: OperatorUser,
    page: PageParams,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> Page[AuditLogResponse]:
    return await AuditService(session).list(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        limit=page.limit,
        offset=page.offset,
    )
