from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


async def test_list_scenarios(client, viewer_headers) -> None:
    resp = await client.get("/api/v1/simulation/scenarios", headers=viewer_headers)
    assert resp.status_code == 200
    keys = [s["key"] for s in resp.json()]
    assert keys == ["hospital_power_failure", "water_supply_disruption", "telecom_outage", "flood_infrastructure_risk"]


async def test_hospital_power_failure_end_to_end(client, operator_headers, admin_headers) -> None:
    # No seed fixture: the simulator provisions the demo topology itself.
    resp = await client.post(
        "/api/v1/simulation/run", json={"scenario": "hospital_power_failure"}, headers=operator_headers
    )
    assert resp.status_code == 200, resp.text
    sim = resp.json()
    assert sim["scenario"] == "hospital_power_failure"
    assert sim["event"]["event_type"] == "POWER_FAILURE"
    assert sim["event"]["payload"]["simulation_id"] == sim["simulation_id"]
    assert sim["incident"]["status"] == "OPEN"
    assert sim["risk"]["level"] == "CRITICAL" and sim["risk"]["score"] >= 80

    infra = {i["name"]: i for i in sim["affected_infrastructure"]}
    services = {s["name"]: s for s in sim["affected_services"]}
    assert infra["Central Power Substation"]["relationship"] == "ORIGIN"
    assert infra["Hyderabad Central Hospital"]["status"] == "DEGRADED"
    assert services["Emergency Healthcare"]["status"] == "DISRUPTED"

    ai = sim["ai_analysis"]
    assert ai["summary"] and ai["potential_impact"] and ai["recommended_actions"]
    assert 0 < ai["confidence"] <= 1
    titles = [r["title"] for r in sim["recommendations"]]
    assert titles[0] == "Activate backup power"
    assert sim["recommendations"][0]["priority"] == "CRITICAL"
    assert sim["human_decision"]["required"] is True
    assert sim["timeline"][-1]["step"] == "HUMAN_DECISION"
    assert sim["audit"]["recorded"] is True and sim["audit"]["entries"] > 5

    audit = await client.get("/api/v1/audit", params={"action": "SIMULATION_RUN"}, headers=admin_headers)
    assert audit.json()["items"][0]["entity_id"] == sim["simulation_id"]


@pytest.mark.parametrize(
    ("scenario", "expected_asset", "level"),
    [
        ("water_supply_disruption", "Hyderabad Central Hospital", "HIGH"),
        ("telecom_outage", "Telecom Tower", "HIGH"),
        ("flood_infrastructure_risk", "Emergency Services Center", "CRITICAL"),
    ],
)
async def test_other_scenarios(client, operator_headers, scenario, expected_asset, level) -> None:
    resp = await client.post("/api/v1/simulation/run", json={"scenario": scenario}, headers=operator_headers)
    assert resp.status_code == 200, resp.text
    sim = resp.json()
    assert expected_asset in {i["name"] for i in sim["affected_infrastructure"]}
    assert sim["risk"]["level"] == level
    assert sim["recommendations"]


async def test_simulation_requires_operator_and_valid_scenario(client, viewer_headers, operator_headers) -> None:
    forbidden = await client.post("/api/v1/simulation/run", json={"scenario": "telecom_outage"}, headers=viewer_headers)
    assert forbidden.status_code == 403
    unknown = await client.post("/api/v1/simulation/run", json={"scenario": "alien_invasion"}, headers=operator_headers)
    assert unknown.status_code == 422
