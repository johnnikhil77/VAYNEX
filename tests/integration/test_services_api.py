from __future__ import annotations

import pytest

from tests.conftest import find_infrastructure

pytestmark = pytest.mark.anyio


async def test_service_crud(client, seeded, operator_headers, viewer_headers) -> None:
    hospital = await find_infrastructure(client, viewer_headers, "Hyderabad Central Hospital")
    created = await client.post(
        "/api/v1/services",
        json={
            "organization_id": hospital["organization_id"],
            "name": "Blood Bank",
            "service_type": "HEALTHCARE",
            "criticality": "HIGH",
            "infrastructure_id": hospital["id"],
        },
        headers=operator_headers,
    )
    assert created.status_code == 201, created.text
    svc = created.json()

    by_infra = await client.get(
        "/api/v1/services", params={"infrastructure_id": hospital["id"]}, headers=viewer_headers
    )
    names = {s["name"] for s in by_infra.json()["items"]}
    assert {"Blood Bank", "Emergency Healthcare", "Hospital Clinical Services"} <= names

    patched = await client.patch(f"/api/v1/services/{svc['id']}", json={"status": "DEGRADED"}, headers=operator_headers)
    assert patched.status_code == 200 and patched.json()["status"] == "DEGRADED"
    assert (await client.get(f"/api/v1/services/{svc['id']}", headers=viewer_headers)).json()["status"] == "DEGRADED"
    assert (
        await client.patch(f"/api/v1/services/{svc['id']}", json={"status": "DEGRADED"}, headers=viewer_headers)
    ).status_code == 403


async def test_dependencies_api(client, seeded, operator_headers, viewer_headers) -> None:
    listed = await client.get("/api/v1/dependencies", params={"limit": 100}, headers=viewer_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 12
    first = listed.json()["items"][0]
    assert first["source"]["name"] and first["target"]["name"]
    assert (await client.get(f"/api/v1/dependencies/{first['id']}", headers=viewer_headers)).status_code == 200

    road = await find_infrastructure(client, viewer_headers, "Critical Road")
    tower = await find_infrastructure(client, viewer_headers, "Telecom Tower")
    body = {
        "source_infrastructure_id": tower["id"],
        "target_infrastructure_id": road["id"],
        "dependency_type": "TELECOM",
        "strength": "LOW",
    }
    created = await client.post("/api/v1/dependencies", json=body, headers=operator_headers)
    assert created.status_code == 201, created.text
    assert (await client.post("/api/v1/dependencies", json=body, headers=operator_headers)).status_code == 409

    self_dep = await client.post(
        "/api/v1/dependencies",
        json={**body, "target_infrastructure_id": tower["id"]},
        headers=operator_headers,
    )
    assert self_dep.status_code == 422
    any_service = (await client.get("/api/v1/services", params={"limit": 1}, headers=viewer_headers)).json()
    two_sources = await client.post(
        "/api/v1/dependencies",
        json={**body, "source_service_id": any_service["items"][0]["id"]},
        headers=operator_headers,
    )
    assert two_sources.status_code == 422

    graph = await client.get("/api/v1/dependencies/graph", headers=viewer_headers)
    assert graph.status_code == 200
    g = graph.json()
    assert len(g["nodes"]) == 14  # 6 assets + 8 services
    node_ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in node_ids and e["target"] in node_ids for e in g["edges"])
