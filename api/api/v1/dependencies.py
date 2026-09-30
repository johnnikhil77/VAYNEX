from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from apps.api.api.v1._common import PageParams
from apps.api.dependencies.auth import DbSession, OperatorUser, ViewerUser
from apps.api.schemas.common import Page
from apps.api.schemas.dependency import DependencyCreate, DependencyGraphResponse, DependencyResponse
from apps.api.services.dependency_service import DependencyService
from packages.common.enums import DependencyStrength, DependencyType

router = APIRouter(prefix="/dependencies", tags=["Dependencies"])


@router.post("", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED)
async def create_dependency(data: DependencyCreate, session: DbSession, user: OperatorUser) -> DependencyResponse:
    return await DependencyService(session).create(data, user)


@router.get("", response_model=Page[DependencyResponse])
async def list_dependencies(
    session: DbSession,
    _: ViewerUser,
    page: PageParams,
    infrastructure_id: uuid.UUID | None = None,
    service_id: uuid.UUID | None = None,
    dependency_type: DependencyType | None = None,
    strength: DependencyStrength | None = None,
) -> Page[DependencyResponse]:
    return await DependencyService(session).list(
        infrastructure_id=infrastructure_id,
        service_id=service_id,
        dependency_type=dependency_type,
        strength=strength,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/graph", response_model=DependencyGraphResponse, summary="Full dependency graph (nodes + edges) for visualisation"
)
async def dependency_graph(session: DbSession, _: ViewerUser) -> DependencyGraphResponse:
    return await DependencyService(session).graph()


@router.get("/{dependency_id}", response_model=DependencyResponse)
async def get_dependency(dependency_id: uuid.UUID, session: DbSession, _: ViewerUser) -> DependencyResponse:
    return await DependencyService(session).get(dependency_id)
