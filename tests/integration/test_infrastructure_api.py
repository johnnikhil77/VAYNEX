from __future__ import annotations

import pytest

from tests.conftest import find_infrastructure

pytestmark = pytest.mark.anyio


async def _org(client, admin_headers) -> str:
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": "Test Power Utility", "organization_type": "POWER_UTILITY"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_infrastructure_crud_and_filters(client, admin_headers, operator_headers, viewer_headers) -> None:
    org_id = await _org(client, admin_headers)
    payload = {
        "organization_id": org_id,
        "name": "North Substation",
        "infrastructure_type": "POWER_SUBSTATION",
        "criticality": "HIGH",
        "latitude": 17.45,
        "longitude": 78.38,
        "metadata": {"voltage_kv": 33},
    }
    created = await client.post("/api/v1/infrastructure", json=payload, headers=operator_headers)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["status"] == "OPERATIONAL"
    assert item["metadata"] == {"voltage_kv": 33}
    assert item["latitude"] == 17.45

    listed = await client.get(
        "/api/v1/infrastructure", params={"type": "POWER_SUBSTATION", "criticality": "HIGH"}, headers=viewer_headers
    )
    assert listed.json()["total"] == 1
    assert (await client.get("/api/v1/infrastructure", params={"type": "HOSPITAL"}, headers=viewer_headers)).json()[
        "total"
    ] == 0

    patched = await client.patch(
        f"/api/v1/infrastructure/{item['id']}",
        json={"status": "MAINTENANCE", "latitude": 17.46, "longitude": 78.39},
        headers=operator_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "MAINTENANCE" and patched.json()["longitude"] == 78.39

    got = await client.get(f"/api/v1/infrastructure/{item['id']}", headers=viewer_headers)
    assert got.json()["name"] == "North Substation"

    assert (await client.delete(f"/api/v1/infrastructure/{item['id']}", headers=operator_headers)).status_code == 403
    assert (await client.delete(f"/api/v1/infrastructure/{item['id']}", headers=admin_headers)).status_code == 204
    missing = await client.get(f"/api/v1/infrastructure/{item['id']}", headers=viewer_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


async def test_viewer_cannot_create_and_bad_input_is_rejected(client, admin_headers, viewer_headers) -> None:
    org_id = await _org(client, admin_headers)
    body = {"organization_id": org_id, "name": "X Asset", "infrastructure_type": "ROAD"}
    forbidden = await client.post("/api/v1/infrastructure", json=body, headers=viewer_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "PERMISSION_DENIED"

    invalid = await client.post(
        "/api/v1/infrastructure", json={**body, "infrastructure_type": "SPACESHIP"}, headers=admin_headers
    )
    assert invalid.status_code == 422
    one_coord = await client.post("/api/v1/infrastructure", json={**body, "latitude": 10}, headers=admin_headers)
    assert one_coord.status_code == 422
    unknown_org = await client.post(
        "/api/v1/infrastructure",
        json={**body, "organization_id": "00000000-0000-0000-0000-000000000000"},
        headers=admin_headers,
    )
    assert unknown_org.status_code == 422
    assert unknown_org.json()["error"]["code"] == "INVALID_REFERENCE"


async def test_infrastructure_dependency_view(client, seeded, viewer_headers) -> None:
    substation = await find_infrastructure(client, viewer_headers, "Central Power Substation")
    resp = await client.get(f"/api/v1/infrastructure/{substation['id']}/dependencies", headers=viewer_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["upstream"] == []
    downstream_targets = {d["target"]["name"] for d in body["downstream"]}
    assert {"Hyderabad Central Hospital", "Emergency Services Center"} <= downstream_targets
    assert [s["name"] for s in body["hosted_services"]] == ["Electricity Distribution"]
    affected_services = {s["name"] for s in body["affected_services"]}
    assert "Emergency Healthcare" in affected_services
