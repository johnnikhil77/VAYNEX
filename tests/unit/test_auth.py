"""Password hashing, JWT and role-hierarchy unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest
from pydantic import ValidationError

from apps.api.core.security import role_satisfies
from apps.api.schemas.auth import RegisterRequest
from packages.common.enums import UserRole
from packages.security.jwt import TokenError, create_access_token, decode_access_token
from packages.security.password import hash_password, needs_rehash, verify_password

SECRET = "unit-test-secret-key-with-at-least-32-bytes"


def test_password_hash_is_argon2id_and_salted() -> None:
    first, second = hash_password("CorrectHorse9"), hash_password("CorrectHorse9")
    assert first.startswith("$argon2id$")
    assert first != second  # unique salt per hash
    assert "CorrectHorse9" not in first
    assert not needs_rehash(first)


def test_password_verification() -> None:
    hashed = hash_password("CorrectHorse9")
    assert verify_password("CorrectHorse9", hashed)
    assert not verify_password("WrongHorse9", hashed)
    assert not verify_password("CorrectHorse9", "not-a-valid-hash")


def test_jwt_round_trip_contains_expected_claims() -> None:
    token = create_access_token(subject="user-123", role="OPERATOR", secret_key=SECRET, expires_minutes=5)
    claims = decode_access_token(token, secret_key=SECRET)
    assert claims["sub"] == "user-123"
    assert claims["role"] == "OPERATOR"
    assert claims["type"] == "access"
    assert claims["iss"] == "vaynex"
    assert claims["exp"] - claims["iat"] == 300


def test_jwt_rejects_expired_tampered_and_foreign_tokens() -> None:
    expired = create_access_token(
        subject="u",
        role="VIEWER",
        secret_key=SECRET,
        expires_minutes=1,
        now=datetime.now(UTC) - timedelta(minutes=10),
    )
    with pytest.raises(TokenError, match="expired"):
        decode_access_token(expired, secret_key=SECRET)

    valid = create_access_token(subject="u", role="VIEWER", secret_key=SECRET)
    with pytest.raises(TokenError):
        decode_access_token(valid, secret_key="a-completely-different-secret-key-0000")
    with pytest.raises(TokenError):
        decode_access_token(valid[:-4] + "abcd", secret_key=SECRET)

    wrong_type = pyjwt.encode(
        {"sub": "u", "iss": "vaynex", "type": "refresh", "iat": 1, "exp": 9_999_999_999}, SECRET, algorithm="HS256"
    )
    with pytest.raises(TokenError, match="type"):
        decode_access_token(wrong_type, secret_key=SECRET)


def test_role_hierarchy() -> None:
    assert role_satisfies(UserRole.ADMIN, UserRole.OPERATOR)
    assert role_satisfies(UserRole.OPERATOR, UserRole.OPERATOR)
    assert role_satisfies(UserRole.OPERATOR, UserRole.VIEWER)
    assert not role_satisfies(UserRole.VIEWER, UserRole.OPERATOR)
    assert not role_satisfies(UserRole.OPERATOR, UserRole.ADMIN)


def test_register_schema_normalises_email_and_enforces_password_policy() -> None:
    req = RegisterRequest(email="  Analyst@Example.ORG ", password="goodpass1")
    assert req.email == "analyst@example.org"
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="goodpass1")
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.co", password="short1")
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.co", password="lettersonly")
