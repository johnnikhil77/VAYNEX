from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


async def test_register_login_me_flow(client) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "New.Analyst@Example.org", "password": "Str0ngPassword", "full_name": "New Analyst"},
    )
    assert reg.status_code == 201, reg.text
    user = reg.json()
    assert user["email"] == "new.analyst@example.org"
    assert user["role"] == "VIEWER"  # self-registration is always read-only
    assert "password" not in reg.text and "password_hash" not in reg.text

    login = await client.post(
        "/api/v1/auth/login", json={"email": "new.analyst@example.org", "password": "Str0ngPassword"}
    )
    assert login.status_code == 200
    token = login.json()
    assert token["token_type"] == "bearer" and token["expires_in"] > 0

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]


async def test_duplicate_registration_conflicts(client) -> None:
    payload = {"email": "dup@example.org", "password": "Str0ngPassword"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_invalid_credentials_and_tokens_are_rejected(client) -> None:
    await client.post("/api/v1/auth/register", json={"email": "x@example.org", "password": "Str0ngPassword"})
    bad = await client.post("/api/v1/auth/login", json={"email": "x@example.org", "password": "wrong-password1"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_CREDENTIALS"
    unknown = await client.post("/api/v1/auth/login", json={"email": "nobody@example.org", "password": "whatever1"})
    assert unknown.status_code == 401

    assert (await client.get("/api/v1/auth/me")).status_code == 401
    garbage = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert garbage.status_code == 401
    assert garbage.json()["error"]["code"] == "INVALID_TOKEN"


async def test_validation_errors_do_not_echo_passwords(client) -> None:
    resp = await client.post("/api/v1/auth/register", json={"email": "bad", "password": "SuperSecret"})
    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert "SuperSecret" not in resp.text
    assert any("email" in d["loc"] for d in body["details"])


async def test_login_is_audited(client, operator_headers, admin_headers) -> None:
    resp = await client.get("/api/v1/audit", params={"action": "USER_LOGIN"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2
