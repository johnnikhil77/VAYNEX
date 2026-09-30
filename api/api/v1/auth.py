from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from apps.api.core.config import Settings
from apps.api.dependencies.auth import CurrentUser, DbSession
from apps.api.dependencies.database import get_settings_dep
from apps.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from apps.api.services.auth_service import AuthService

SettingsDep = Annotated[Settings, Depends(get_settings_dep)]

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account (VIEWER role)",
)
async def register(data: RegisterRequest, session: DbSession, settings: SettingsDep) -> UserResponse:
    return await AuthService(session, settings).register(data)


@router.post("/login", response_model=TokenResponse, summary="Obtain a JWT access token")
async def login(data: LoginRequest, session: DbSession, settings: SettingsDep) -> TokenResponse:
    return await AuthService(session, settings).login(data)


@router.get("/me", response_model=UserResponse, summary="Current user")
async def me(user: CurrentUser) -> UserResponse:
    return AuthService.me(user)
