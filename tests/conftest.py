"""Shared pytest fixtures.

Unit tests need nothing external. Integration tests need PostgreSQL (with
PostGIS) and optionally Redis; they are skipped automatically when the test
database is unreachable.

Environment variables:
  TEST_DATABASE_URL   default postgresql+asyncpg://vaynex:vaynex@localhost:5433/vaynex_test
  TEST_REDIS_URL      default redis://localhost:6380/15   (empty string = no Redis)
  VAYNEX_TEST_USE_EXISTING_SCHEMA=1
                      use a schema already created by `alembic upgrade head`
                      instead of create_all (tables are still truncated per test)
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text

from apps.api.core.config import Settings
from apps.api.main import create_app
from packages.common.enums import UserRole
from packages.database.models import Base, User
from packages.database.session import create_engine, create_session_factory
from packages.security.password import hash_password

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://vaynex:vaynex@localhost:5433/vaynex_test")
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6380/15")
USE_EXISTING_SCHEMA = os.getenv("VAYNEX_TEST_USE_EXISTING_SCHEMA", "0") == "1"
TEST_JWT_SECRET = "test-secret-key-that-is-long-enough-for-hs256"

TABLES = (
    "audit_logs, recommendations, risks, incidents, events, dependencies, services, "
    "infrastructure, organizations, users"
)

PASSWORDS = {
    UserRole.ADMIN: "AdminPass123!",
    UserRole.OPERATOR: "OperatorPass123!",
    UserRole.VIEWER: "ViewerPass123!",
}


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


def make_test_settings() -> Settings:
    return Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DATABASE_URL,
        DATABASE_USE_NULL_POOL=True,
        REDIS_URL=TEST_REDIS_URL,
        JWT_SECRET_KEY=TEST_JWT_SECRET,
        AI_PROVIDER="mock",
        OPENAI_API_KEY=None,
        LOG_LEVEL="WARNING",
        DASHBOARD_CACHE_TTL_SECONDS=30,
    )


async def _prepare_schema() -> str | None:
    engine = create_engine(TEST_DATABASE_URL, null_pool=True)
    try:
        async with engine.begin() as conn:
            if not USE_EXISTING_SCHEMA:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
        return None
    except Exception as exc:  # database unreachable / misconfigured
        return f"{type(exc).__name__}: {exc}"
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_ready() -> None:
    error = asyncio.run(_prepare_schema())
    if error:
        pytest.skip(f"Integration database unavailable ({TEST_DATABASE_URL}): {error}")


async def _truncate() -> None:
    engine = create_engine(TEST_DATABASE_URL, null_pool=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    finally:
        await engine.dispose()


async def _flush_redis() -> None:
    if not TEST_REDIS_URL:
        return
    from redis.asyncio import Redis

    client = Redis.from_url(TEST_REDIS_URL, socket_connect_timeout=0.5)
    try:
        await client.flushdb()
    except Exception:
        pass
    finally:
        await client.aclose()


@pytest.fixture
async def app(database_ready: None) -> AsyncIterator:
    await _truncate()
    await _flush_redis()
    application = create_app(make_test_settings())
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def session(app) -> AsyncIterator:
    factory = create_session_factory(app.state.database.engine)
    async with factory() as s:
        yield s


async def _create_user(app, role: UserRole) -> User:
    factory = create_session_factory(app.state.database.engine)
    async with factory() as s:
        user = User(
            email=f"{role.value.lower()}@test.vaynex.local",
            full_name=f"Test {role.value.title()}",
            role=role,
            password_hash=hash_password(PASSWORDS[role]),
            is_active=True,
        )
        s.add(user)
        await s.commit()
        return user


async def _headers(client: httpx.AsyncClient, app, role: UserRole) -> dict[str, str]:
    user = await _create_user(app, role)
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORDS[role]})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def admin_headers(client, app) -> dict[str, str]:
    return await _headers(client, app, UserRole.ADMIN)


@pytest.fixture
async def operator_headers(client, app) -> dict[str, str]:
    return await _headers(client, app, UserRole.OPERATOR)


@pytest.fixture
async def viewer_headers(client, app) -> dict[str, str]:
    return await _headers(client, app, UserRole.VIEWER)


@pytest.fixture
async def seeded(app) -> None:
    """Hyderabad demo topology (no demo users)."""
    from apps.api.services.demo_data import seed_demo_data

    factory = create_session_factory(app.state.database.engine)
    async with factory() as s:
        await seed_demo_data(s, with_users=False)
        await s.commit()


async def find_infrastructure(client: httpx.AsyncClient, headers: dict[str, str], name: str) -> dict:
    resp = await client.get("/api/v1/infrastructure", params={"search": name}, headers=headers)
    assert resp.status_code == 200, resp.text
    items = [i for i in resp.json()["items"] if i["name"] == name]
    assert items, f"{name} not found"
    return items[0]
