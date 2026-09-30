"""JWT access-token creation and validation (PyJWT)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

ISSUER = "vaynex"
TOKEN_TYPE_ACCESS = "access"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired or has a bad signature."""


def create_access_token(
    *,
    subject: str,
    role: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_minutes: int = 60,
    now: datetime | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": TOKEN_TYPE_ACCESS,
        "iss": ISSUER,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=expires_minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update({k: v for k, v in extra_claims.items() if k not in payload})
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, *, secret_key: str, algorithm: str = "HS256") -> dict[str, Any]:
    """Validate signature, expiry, issuer and token type; return the claims."""
    if not token:
        raise TokenError("Missing token")
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token") from exc
    if claims.get("type") != TOKEN_TYPE_ACCESS:
        raise TokenError("Invalid token type")
    return claims
