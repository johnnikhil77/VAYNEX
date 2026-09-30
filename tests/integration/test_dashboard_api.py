from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


async def test_dashboard_overview_reflects_state_and_caches(client, seeded, operator_headers, viewer_headers) -> None:
    before = await client.get("/api/v1/dashboard/overview", headers=viewer_headers)
    assert before.status_code == 200
    data = before.json()
    assert data["total_infrastructure"] == 6
    assert data["operational_infrastructure"] == 6
    assert data["total_services"] == 8
    assert data["active_incidents"] == 0
    assert len(data["critical_infrastructure"]) == 4

    sim = await client.post(
        "/api/v1/simulation/run", json={"scenario": "hospital_power_failure"}, headers=operator_headers
    )
    assert sim.status_code == 200

    after = (await client.get("/api/v1/dashboard/overview", headers=viewer_headers)).json()
    assert after["cached"] is False  # cache invalidated by the new event
    assert after["active_incidents"] == 1
    assert after["critical_incidents"] == 1
    assert after["failed_infrastructure"] == 1
    assert after["degraded_infrastructure"] >= 1
    assert after["average_risk"] == sim.json()["risk"]["score"]
    assert after["recent_events"][0]["event_type"] == "POWER_FAILURE"
    assert after["recent_incidents"][0]["risk"]["level"] == "CRITICAL"
    assert after["critical_infrastructure"][0]["status"] == "FAILED"  # failed assets listed first

    cached = (await client.get("/api/v1/dashboard/overview", headers=viewer_headers)).json()
    if cached["cached"] is False:  # pragma: no cover - Redis not available in this environment
        pytest.skip("Redis not available; cache path not exercised")
    assert cached["active_incidents"] == 1


async def test_dashboard_works_without_redis(client, app, viewer_headers) -> None:
    from apps.api.core.cache import Cache

    app.state.cache = Cache("redis://127.0.0.1:1/0", timeout=0.2)  # nothing listens on port 1
    resp = await client.get("/api/v1/dashboard/overview", headers=viewer_headers)
    assert resp.status_code == 200
    assert resp.json()["cached"] is False
    ready = await client.get("/api/v1/health/ready")
    assert ready.status_code == 200 and ready.json()["status"] == "degraded"
    await app.state.cache.close()


async def test_dashboard_requires_authentication(client) -> None:
    resp = await client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NOT_AUTHENTICATED"
