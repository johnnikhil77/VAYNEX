from __future__ import annotations

import pytest

from tests.conftest import find_infrastructure

pytestmark = pytest.mark.anyio


async def test_event_ingestion_runs_full_pipeline(client, seeded, operator_headers, viewer_headers) -> None:
    substation = await find_infrastructure(client, viewer_headers, "Central Power Substation")
    resp = await client.post(
        "/api/v1/events",
        json={
            "event_type": "POWER_FAILURE",
            "source": "grid-monitor",
            "severity": "HIGH",
            "title": "Central Substation Power Failure",
            "description": "Unexpected power interruption",
            "infrastructure_id": substation["id"],
            "payload": {"voltage": 0, "duration_minutes": 12},
        },
        headers=operator_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["pipeline"] == [
        "EVENT_CREATED",
        "INFRASTRUCTURE_CONTEXT",
        "DEPENDENCIES_ANALYZED",
        "INCIDENT_DETECTED",
        "RISK_ASSESSED",
        "AI_ANALYSIS",
        "RECOMMENDATIONS",
        "AUDIT",
    ]
    assert body["incident_created"] is True
    assert body["event"]["latitude"] == substation["latitude"]  # inherited from the asset
    affected = {i["name"] for i in body["affected_infrastructure"]}
    assert "Hyderabad Central Hospital" in affected
    assert body["risk"]["level"] in {"HIGH", "CRITICAL"}
    assert body["incident"]["severity"] == body["risk"]["level"]
    sources = {r["source"] for r in body["recommendations"]}
    assert sources == {"RULE_ENGINE", "AI"}
    assert all(r["status"] == "PENDING" for r in body["recommendations"])

    # the observed failure is reflected in asset status
    refreshed = await client.get(f"/api/v1/infrastructure/{substation['id']}", headers=viewer_headers)
    assert refreshed.json()["status"] == "FAILED"

    listed = await client.get("/api/v1/events", params={"event_type": "POWER_FAILURE"}, headers=viewer_headers)
    assert listed.json()["total"] == 1
    got = await client.get(f"/api/v1/events/{body['event']['id']}", headers=viewer_headers)
    assert got.json()["payload"]["duration_minutes"] == 12


async def test_low_severity_event_on_low_criticality_asset_creates_no_incident(
    client, admin_headers, operator_headers
) -> None:
    org = await client.post(
        "/api/v1/organizations", json={"name": "Parks Dept", "organization_type": "MUNICIPAL"}, headers=admin_headers
    )
    asset = await client.post(
        "/api/v1/infrastructure",
        json={
            "organization_id": org.json()["id"],
            "name": "Park Lighting",
            "infrastructure_type": "ROAD",
            "criticality": "LOW",
        },
        headers=operator_headers,
    )
    resp = await client.post(
        "/api/v1/events",
        json={
            "event_type": "SENSOR_ALERT",
            "source": "iot",
            "severity": "LOW",
            "title": "Lamp flicker",
            "infrastructure_id": asset.json()["id"],
        },
        headers=operator_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_created"] is False and body["incident"] is None
    assert body["pipeline"][-2:] == ["NO_INCIDENT", "AUDIT"]


async def test_event_validation(client, operator_headers, viewer_headers) -> None:
    base = {"event_type": "POWER_FAILURE", "source": "x", "severity": "HIGH", "title": "Test event"}
    assert (await client.post("/api/v1/events", json=base, headers=viewer_headers)).status_code == 403
    bad_ref = await client.post(
        "/api/v1/events",
        json={**base, "infrastructure_id": "00000000-0000-0000-0000-000000000000"},
        headers=operator_headers,
    )
    assert bad_ref.status_code == 422
    bad_sev = await client.post("/api/v1/events", json={**base, "severity": "APOCALYPTIC"}, headers=operator_headers)
    assert bad_sev.status_code == 422
    bad_radius = await client.post(
        "/api/v1/events",
        json={**base, "latitude": 17.4, "longitude": 78.4, "payload": {"impact_radius_m": -5}},
        headers=operator_headers,
    )
    assert bad_radius.status_code == 422


async def test_spatial_exposure_radius(client, seeded, operator_headers) -> None:
    resp = await client.post(
        "/api/v1/events",
        json={
            "event_type": "FIRE",
            "source": "fire-dept",
            "severity": "HIGH",
            "title": "Warehouse fire",
            "latitude": 17.4000,
            "longitude": 78.4800,
            "payload": {"impact_radius_m": 500},
        },
        headers=operator_headers,
    )
    assert resp.status_code == 201, resp.text
    exposed = [i for i in resp.json()["affected_infrastructure"] if i["relationship"] == "DIRECT_EXPOSURE"]
    names = {i["name"] for i in exposed}
    assert "Hyderabad Central Hospital" in names  # ~0 m away
    assert "Water Treatment Plant" not in names  # ~4 km away
    assert all(i["distance_m"] <= 500 for i in exposed)
