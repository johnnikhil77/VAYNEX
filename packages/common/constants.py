"""Shared constants: level weights, graph limits, cache keys, demo asset names."""

from __future__ import annotations

from typing import Final

# Numeric weight for any LOW/MEDIUM/HIGH/CRITICAL style level.
LEVEL_WEIGHTS: Final[dict[str, float]] = {
    "LOW": 0.25,
    "MEDIUM": 0.5,
    "HIGH": 0.75,
    "CRITICAL": 1.0,
}

LEVEL_ORDER: Final[dict[str, int]] = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

# Dependency propagation (impact analysis)
MAX_PROPAGATION_DEPTH: Final[int] = 5
MIN_PROPAGATION_WEIGHT: Final[float] = 0.25
HOSTED_SERVICE_WEIGHT: Final[float] = 1.0  # a service hosted on an asset fails with it
DIRECT_EXPOSURE_WEIGHT: Final[float] = 0.75  # asset inside a hazard radius
DEFAULT_IMPACT_RADIUS_M: Final[float] = 0.0  # spatial search disabled unless requested
MAX_IMPACT_RADIUS_M: Final[float] = 50_000.0

# Cache
DASHBOARD_CACHE_KEY: Final[str] = "vaynex:dashboard:overview"

# Pagination
DEFAULT_PAGE_LIMIT: Final[int] = 50
MAX_PAGE_LIMIT: Final[int] = 200

# Demo organisation / asset names (shared by the seed script and the simulator)
DEMO_ORG_MUNICIPAL: Final[str] = "Hyderabad Municipal Operations"
DEMO_ORG_HEALTHCARE: Final[str] = "Hyderabad Emergency Healthcare Network"
DEMO_ORG_POWER: Final[str] = "Telangana Power Operations"
DEMO_ORG_WATER: Final[str] = "Regional Water Authority"
DEMO_ORG_TELECOM: Final[str] = "Telecom Operations Network"

DEMO_HOSPITAL: Final[str] = "Hyderabad Central Hospital"
DEMO_SUBSTATION: Final[str] = "Central Power Substation"
DEMO_WATER_PLANT: Final[str] = "Water Treatment Plant"
DEMO_TELECOM_TOWER: Final[str] = "Telecom Tower"
DEMO_EMERGENCY_CENTER: Final[str] = "Emergency Services Center"
DEMO_ROAD: Final[str] = "Critical Road"

DEMO_SVC_EMERGENCY_HEALTHCARE: Final[str] = "Emergency Healthcare"
DEMO_SVC_CLINICAL: Final[str] = "Hospital Clinical Services"
DEMO_SVC_ELECTRICITY: Final[str] = "Electricity Distribution"
DEMO_SVC_WATER: Final[str] = "Water Supply Service"
DEMO_SVC_TELECOM: Final[str] = "Telecommunications"
DEMO_SVC_EMERGENCY_COMMS: Final[str] = "Emergency Communications"
DEMO_SVC_EMERGENCY_RESPONSE: Final[str] = "Emergency Response & Dispatch"
DEMO_SVC_MOBILITY: Final[str] = "Urban Mobility Corridor"

ADVISORY_NOTICE: Final[str] = (
    "Vaynex is an advisory decision-support system. It never controls physical "
    "infrastructure; every action requires an authorized human operator."
)
