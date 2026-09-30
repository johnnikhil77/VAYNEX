from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


async def test_health_ok_with_request_id(client) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert len(resp.headers["X-Request-ID"]) >= 8


async def test_inbound_request_id_is_propagated(client) -> None:
    resp = await client.get("/api/v1/health", headers={"X-Request-ID": "frontend-trace-0001"})
    assert resp.headers["X-Request-ID"] == "frontend-trace-0001"


async def test_readiness_checks_postgres_and_redis(client) -> None:
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["checks"]["postgres"]["status"] == "ok"
    assert "redis" in body["checks"] and "postgis" in body["checks"]


async def test_unknown_route_uses_error_envelope(client) -> None:
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    error = resp.json()["error"]
    assert error["code"] == "RESOURCE_NOT_FOUND"
    assert error["request_id"] == resp.headers["X-Request-ID"]


async def test_openapi_and_docs_available(client) -> None:
    spec = (await client.get("/openapi.json")).json()
    assert "/api/v1/simulation/run" in spec["paths"]
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/redoc")).status_code == 200
