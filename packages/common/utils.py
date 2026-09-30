"""Small, dependency-free helpers."""

from __future__ import annotations

import math
import re
import uuid
from datetime import UTC, datetime

from packages.common.constants import LEVEL_ORDER, LEVEL_WEIGHTS

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)+$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9\-_.]{8,128}$")

EARTH_RADIUS_M = 6_371_008.8


def utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(UTC)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def normalize_email(value: str) -> str:
    """Trim + lowercase and validate an e-mail address. Raises ``ValueError``."""
    email = value.strip().lower()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise ValueError("Invalid email address")
    return email


def is_valid_request_id(value: str | None) -> bool:
    return bool(value) and bool(_REQUEST_ID_RE.match(value or ""))


def level_weight(level: str | None) -> float:
    """Weight in [0, 1] for LOW/MEDIUM/HIGH/CRITICAL (0.0 for None/unknown)."""
    if level is None:
        return 0.0
    return LEVEL_WEIGHTS.get(str(level), 0.0)


def max_level(levels: list[str]) -> str | None:
    """Return the most severe level in ``levels`` (or None if empty)."""
    known = [lvl for lvl in levels if lvl in LEVEL_ORDER]
    if not known:
        return None
    return max(known, key=lambda lvl: LEVEL_ORDER[lvl])


def round_half_up(value: float) -> int:
    """Deterministic rounding (avoids banker's rounding surprises)."""
    return int(math.floor(value + 0.5))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 coordinates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
