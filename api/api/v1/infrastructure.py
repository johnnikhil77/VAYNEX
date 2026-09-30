from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from apps.api.api.v1._common import CacheDep, PageParams
from apps.api.dependencies.auth import AdminUser, DbSession, OperatorUser, ViewerUser
from apps.api.schemas.common import Page
from apps.api.schemas.dependency import InfrastructureDependenciesResponse
from apps.api.schemas.infrastructure import (
    InfrastructureCreate,
    InfrastructureResponse,
    InfrastructureUpdate,
)
from apps.api.services.infrastructure_service import InfrastructureService
from packages.common.enums import Criticality, InfrastructureStatus, InfrastructureType

router = APIRouter(prefix="/infrastructure", tags=["Infrastructure"])


@router.post("", response_model=InfrastructureResponse, status_code=status.HTTP_201_CREATED)
async def create_infrastructure(
    data: InfrastructureCreate, session: DbSession, cache: CacheDep, user: OperatorUser
) -> InfrastructureResponse:
    return await InfrastructureService(session, cache).create(data, user)


@router.get("", response_model=Page[InfrastructureResponse])
async def list_infrastructure(
    session: DbSession,
    _: ViewerUser,
    page: PageParams,
    organization_id: uuid.UUID | None = None,
    infrastructure_type: Annotated[InfrastructureType | None, Query(alias="type")] = None,
    status_: Annotated[InfrastructureStatus | None, Query(alias="status")] = None,
    criticality: Criticality | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[InfrastructureResponse]:
    return await InfrastructureService(session).list(
        organization_id=organization_id,
        infrastructure_type=infrastructure_type,
        status=status_,
        criticality=criticality,
        search=search,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{infrastructure_id}", response_model=InfrastructureResponse)
async def get_infrastructure(infrastructure_id: uuid.UUID, session: DbSession, _: ViewerUser) -> InfrastructureResponse:
    return await InfrastructureService(session).get(infrastructure_id)


@router.patch("/{infrastructure_id}", response_model=InfrastructureResponse)
async def update_infrastructure(
    infrastructure_id: uuid.UUID, data: InfrastructureUpdate, session: DbSession, cache: CacheDep, user: OperatorUser
) -> InfrastructureResponse:
    return await InfrastructureService(session, cache).update(infrastructure_id, data, user)


@router.delete("/{infrastructure_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_infrastructure(
    infrastructure_id: uuid.UUID, session: DbSession, cache: CacheDep, user: AdminUser
) -> Response:
    await InfrastructureService(session, cache).delete(infrastructure_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{infrastructure_id}/dependencies",
    response_model=InfrastructureDependenciesResponse,
    summary="Upstream/downstream dependencies and cascading impact of this asset",
)
async def infrastructure_dependencies(
    infrastructure_id: uuid.UUID, session: DbSession, _: ViewerUser
) -> InfrastructureDependenciesResponse:
    return await InfrastructureService(session).dependencies(infrastructure_id)
