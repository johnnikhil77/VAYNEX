from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from apps.api.api.v1._common import PageParams
from apps.api.dependencies.auth import AdminUser, DbSession, ViewerUser
from apps.api.schemas.common import Page
from apps.api.schemas.organization import OrganizationCreate, OrganizationResponse
from apps.api.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(data: OrganizationCreate, session: DbSession, user: AdminUser) -> OrganizationResponse:
    return await OrganizationService(session).create(data, user)


@router.get("", response_model=Page[OrganizationResponse])
async def list_organizations(session: DbSession, _: ViewerUser, page: PageParams) -> Page[OrganizationResponse]:
    return await OrganizationService(session).list(limit=page.limit, offset=page.offset)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(organization_id: uuid.UUID, session: DbSession, _: ViewerUser) -> OrganizationResponse:
    return await OrganizationService(session).get(organization_id)
