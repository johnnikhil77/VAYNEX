"""Deterministic scoring weights and rule-based recommendation catalogue.

Everything here is plain data so it can be reviewed, unit-tested and tuned
without touching the engine code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------
# Maximum number of points each factor can contribute. Sum == 100.
FACTOR_MAX_POINTS: Final[dict[str, float]] = {
    "event_severity": 25.0,
    "infrastructure_criticality": 25.0,
    "dependency_strength": 15.0,
    "affected_infrastructure": 15.0,
    "affected_services": 20.0,
}

# Each affected node contributes criticality_weight x impact_weight (how strongly
# the disruption reaches it). A cascade whose summed contribution reaches the
# saturation value scores the full factor points, e.g. four CRITICAL assets
# hit at full strength, or five CRITICAL services.
INFRASTRUCTURE_SATURATION: Final[float] = 4.0
SERVICE_SATURATION: Final[float] = 5.0

# Level thresholds (inclusive lower bounds), evaluated from the top down.
LEVEL_THRESHOLDS: Final[list[tuple[int, str]]] = [
    (80, "CRITICAL"),
    (60, "HIGH"),
    (30, "MEDIUM"),
    (0, "LOW"),
]


def level_for_score(score: int) -> str:
    for threshold, level in LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "LOW"


# ---------------------------------------------------------------------------
# Rule-engine recommendations
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RecommendationRule:
    """A recommendation fired when its conditions match the incident context.

    ``event_types`` / ``affected_infrastructure_types`` / ``affected_service_types``
    are OR-ed within a field and AND-ed across fields; an empty tuple means
    "no condition on this field". ``min_risk_level`` gates low-risk incidents.
    """

    key: str
    title: str
    description: str
    priority: str
    event_types: tuple[str, ...] = ()
    affected_infrastructure_types: tuple[str, ...] = ()
    affected_service_types: tuple[str, ...] = ()
    min_risk_level: str = "LOW"


RECOMMENDATION_RULES: Final[tuple[RecommendationRule, ...]] = (
    RecommendationRule(
        key="activate_backup_power",
        title="Activate backup power",
        description=(
            "Request facility operators to switch critical loads to backup generators / UPS "
            "and verify fuel reserves for at least 12 hours."
        ),
        priority="CRITICAL",
        event_types=("POWER_FAILURE", "FLOOD"),
        affected_infrastructure_types=("HOSPITAL", "EMERGENCY_CENTER", "DATA_CENTER", "WATER_TREATMENT"),
    ),
    RecommendationRule(
        key="dispatch_grid_crew",
        title="Dispatch grid restoration crew",
        description=(
            "Ask the power utility to dispatch a field crew to the failed substation and "
            "prioritise feeders that supply critical facilities."
        ),
        priority="HIGH",
        event_types=("POWER_FAILURE",),
    ),
    RecommendationRule(
        key="divert_ambulances",
        title="Divert incoming ambulances",
        description=(
            "Coordinate with the emergency healthcare network to divert non-critical ambulance "
            "arrivals to nearby hospitals until capacity is confirmed."
        ),
        priority="CRITICAL",
        affected_service_types=("EMERGENCY_HEALTHCARE",),
        min_risk_level="HIGH",
    ),
    RecommendationRule(
        key="deploy_water_tankers",
        title="Deploy emergency water tankers",
        description=(
            "Arrange potable water tankers for hospitals and emergency facilities and issue a "
            "conservation advisory for affected zones."
        ),
        priority="HIGH",
        event_types=("WATER_DISRUPTION", "FLOOD"),
        affected_service_types=("WATER_SUPPLY", "HEALTHCARE", "EMERGENCY_HEALTHCARE"),
    ),
    RecommendationRule(
        key="water_quality_testing",
        title="Increase water quality sampling",
        description="Schedule additional water quality tests before supply is restored.",
        priority="MEDIUM",
        event_types=("WATER_DISRUPTION", "FLOOD"),
        affected_infrastructure_types=("WATER_TREATMENT", "WATER_PIPELINE"),
    ),
    RecommendationRule(
        key="activate_backup_comms",
        title="Activate backup emergency communications",
        description=(
            "Switch emergency dispatch to satellite phones / VHF radio and confirm connectivity "
            "with hospitals and field units."
        ),
        priority="CRITICAL",
        event_types=("TELECOM_OUTAGE", "POWER_FAILURE", "FLOOD"),
        affected_service_types=("EMERGENCY_COMMUNICATIONS", "TELECOMMUNICATIONS"),
    ),
    RecommendationRule(
        key="deploy_mobile_cell",
        title="Request mobile cell-on-wheels deployment",
        description="Ask the telecom operator to deploy temporary mobile towers for coverage restoration.",
        priority="HIGH",
        event_types=("TELECOM_OUTAGE",),
    ),
    RecommendationRule(
        key="reroute_traffic",
        title="Reroute traffic and secure access routes",
        description=(
            "Coordinate with traffic police to close flooded road segments and publish alternate "
            "routes that keep hospital and emergency access open."
        ),
        priority="HIGH",
        event_types=("FLOOD", "TRAFFIC_DISRUPTION", "EARTHQUAKE"),
        affected_infrastructure_types=("ROAD", "BRIDGE"),
    ),
    RecommendationRule(
        key="preposition_responders",
        title="Pre-position emergency response teams",
        description="Stage rescue and medical response teams near affected critical facilities.",
        priority="HIGH",
        event_types=("FLOOD", "EARTHQUAKE", "FIRE"),
        min_risk_level="MEDIUM",
    ),
    RecommendationRule(
        key="notify_stakeholders",
        title="Notify affected service owners",
        description=(
            "Inform the owning organisations of all affected infrastructure and services and "
            "request status confirmation within 30 minutes."
        ),
        priority="MEDIUM",
        min_risk_level="MEDIUM",
    ),
    RecommendationRule(
        key="public_advisory",
        title="Issue public advisory",
        description=(
            "Prepare a public communication describing affected services, expected duration and "
            "alternatives. Requires approval by the incident commander."
        ),
        priority="HIGH",
        min_risk_level="HIGH",
    ),
    RecommendationRule(
        key="monitor",
        title="Continue monitoring",
        description="Keep the asset under observation and re-evaluate risk if conditions change.",
        priority="LOW",
    ),
)
