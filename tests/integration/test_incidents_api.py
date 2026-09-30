from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


async def _simulate(client, headers, scenario="hospital_power_failure") -> dict:
    resp = await client.post("/api/v1/simulation/run", json={"scenario": scenario}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_incident_detail_contains_full_context(client, operator_headers, viewer_headers) -> None:
    sim = await _simulate(client, operator_headers)
    incident_id = sim["incident"]["id"]
    resp = await client.get(f"/api/v1/incidents/{incident_id}", headers=viewer_headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["event"]["event_type"] == "POWER_FAILURE"
    assert detail["affected_infrastructure"] and detail["affected_services"]
    assert detail["risk_assessment"]["score"] == sim["risk"]["score"]
    assert detail["ai_analysis"]["summary"]
    assert len(detail["recommendations"]) == len(sim["recommendations"])

    listed = await client.get("/api/v1/incidents", params={"active_only": True}, headers=viewer_headers)
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["risk"]["level"] == "CRITICAL"


async def test_operator_decision_updates_incident_and_audit(client, operator_headers, admin_headers) -> None:
    sim = await _simulate(client, operator_headers)
    incident_id = sim["incident"]["id"]
    rec_id = sim["recommendations"][0]["id"]

    accepted = await client.patch(
        f"/api/v1/recommendations/{rec_id}", json={"status": "ACCEPTED", "note": "Approved"}, headers=operator_headers
    )
    assert accepted.status_code == 200
    assert accepted.json()["decided_by"] is not None

    invalid = await client.patch(
        f"/api/v1/recommendations/{rec_id}", json={"status": "REJECTED"}, headers=operator_headers
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    done = await client.patch(
        f"/api/v1/recommendations/{rec_id}", json={"status": "COMPLETED"}, headers=operator_headers
    )
    assert done.json()["status"] == "COMPLETED"

    other = sim["recommendations"][1]["id"]
    rejected = await client.patch(
        f"/api/v1/recommendations/{other}", json={"status": "REJECTED"}, headers=operator_headers
    )
    assert rejected.json()["status"] == "REJECTED"

    incident = (await client.get(f"/api/v1/incidents/{incident_id}", headers=operator_headers)).json()
    assert incident["status"] == "MITIGATING"

    audit = (await client.get("/api/v1/audit", params={"limit": 200}, headers=admin_headers)).json()
    actions = {a["action"] for a in audit["items"]}
    assert {"RECOMMENDATION_ACCEPTED", "RECOMMENDATION_REJECTED", "RECOMMENDATION_COMPLETED"} <= actions


async def test_patch_and_resolve_restores_asset_status(client, operator_headers, viewer_headers) -> None:
    sim = await _simulate(client, operator_headers)
    incident_id = sim["incident"]["id"]
    origin_id = sim["event"]["infrastructure_id"]
    assert (await client.get(f"/api/v1/infrastructure/{origin_id}", headers=viewer_headers)).json()[
        "status"
    ] == "FAILED"

    patched = await client.patch(
        f"/api/v1/incidents/{incident_id}", json={"status": "INVESTIGATING"}, headers=operator_headers
    )
    assert patched.status_code == 200 and patched.json()["status"] == "INVESTIGATING"
    bad = await client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "RESOLVED"}, headers=operator_headers)
    assert bad.status_code == 422

    resolved = await client.post(
        f"/api/v1/incidents/{incident_id}/resolve", json={"resolution_note": "Grid restored"}, headers=operator_headers
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED" and resolved.json()["resolved_at"]
    assert (await client.get(f"/api/v1/infrastructure/{origin_id}", headers=viewer_headers)).json()[
        "status"
    ] == "OPERATIONAL"

    again = await client.post(f"/api/v1/incidents/{incident_id}/resolve", headers=operator_headers)
    assert again.status_code == 409
    assert (
        await client.get("/api/v1/incidents/00000000-0000-0000-0000-000000000000", headers=viewer_headers)
    ).status_code == 404


async def test_reanalysis_and_risk_endpoints(client, operator_headers, viewer_headers) -> None:
    sim = await _simulate(client, operator_headers, "telecom_outage")
    incident_id = sim["incident"]["id"]

    analysis = await client.post(f"/api/v1/intelligence/analyze/{incident_id}", headers=operator_headers)
    assert analysis.status_code == 200
    assert analysis.json()["new_recommendations"] == []  # identical AI actions are de-duplicated
    assert analysis.json()["ai_analysis"]["provider"] == "mock"

    history = await client.get(f"/api/v1/risk/incidents/{incident_id}", headers=viewer_headers)
    assert history.json()["latest"]["score"] == sim["risk"]["score"]
    recalculated = await client.post(f"/api/v1/risk/incidents/{incident_id}/recalculate", headers=operator_headers)
    assert recalculated.json()["score"] == sim["risk"]["score"]  # deterministic
    assert (
        len((await client.get(f"/api/v1/risk/incidents/{incident_id}", headers=viewer_headers)).json()["history"]) == 2
    )

    what_if = await client.post(
        "/api/v1/risk/evaluate", json={"event_severity": "LOW", "origin_criticality": "LOW"}, headers=viewer_headers
    )
    assert what_if.json()["level"] == "LOW"
    provider = await client.get("/api/v1/intelligence/provider", headers=viewer_headers)
    assert provider.json() == {"provider": "mock", "model": "vaynex-mock-analyst-v1", "external": False}
