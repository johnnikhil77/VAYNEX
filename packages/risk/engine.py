"""Deterministic risk engine.

The engine is a pure function of its input: the same ``RiskInput`` always
produces exactly the same ``RiskResult``. No randomness, no clock, no I/O.

Score (0-100) is the sum of five explainable factor contributions:
(affected nodes contribute criticality weight x impact weight, saturating at
4.0 for infrastructure and 5.0 for services)

=========================== ====== ==========================================
factor                      max    measure
=========================== ====== ==========================================
event_severity              25     severity weight of the triggering event
infrastructure_criticality  25     criticality of the origin asset
dependency_strength         15     strongest dependency edge in the cascade
affected_infrastructure     15     summed criticality of downstream assets
affected_services           20     summed criticality of affected services
=========================== ====== ==========================================

Weights: LOW=0.25, MEDIUM=0.5, HIGH=0.75, CRITICAL=1.0.
Levels: 0-29 LOW, 30-59 MEDIUM, 60-79 HIGH, 80-100 CRITICAL.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from packages.common.utils import clamp, level_weight, max_level, round_half_up
from packages.risk.rules import (
    FACTOR_MAX_POINTS,
    INFRASTRUCTURE_SATURATION,
    RECOMMENDATION_RULES,
    SERVICE_SATURATION,
    RecommendationRule,
    level_for_score,
)

_LEVEL_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@dataclass(frozen=True, slots=True)
class RiskInput:
    event_severity: str
    origin_criticality: str | None = None
    dependency_strengths: Sequence[str] = field(default_factory=tuple)
    affected_infrastructure_criticalities: Sequence[str] = field(default_factory=tuple)
    affected_service_criticalities: Sequence[str] = field(default_factory=tuple)
    # Optional per-node impact weights (0-1, same order as the criticalities).
    # When omitted every affected node counts at full strength (1.0).
    affected_infrastructure_impact: Sequence[float] | None = None
    affected_service_impact: Sequence[float] | None = None
    event_type: str | None = None
    origin_name: str | None = None


@dataclass(frozen=True, slots=True)
class RiskFactor:
    name: str
    input: Any
    weight: float
    max_points: float
    points: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "input": self.input,
            "weight": round(self.weight, 4),
            "max_points": self.max_points,
            "points": round(self.points, 2),
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class RiskResult:
    score: int
    level: str
    impact_score: int
    likelihood_score: int
    affected_infrastructure_count: int
    affected_services_count: int
    explanation: str
    factors: tuple[RiskFactor, ...]

    def factors_as_dicts(self) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self.factors]


def _saturating(weights: Iterable[float], saturation: float) -> float:
    return clamp(sum(weights) / saturation, 0.0, 1.0)


def _weighted(criticalities: Sequence[str], impacts: Sequence[float] | None) -> list[float]:
    if impacts is not None and len(impacts) != len(criticalities):
        raise ValueError("impact weights must match the number of affected nodes")
    factors = impacts if impacts is not None else [1.0] * len(criticalities)
    return [level_weight(c) * clamp(float(w), 0.0, 1.0) for c, w in zip(criticalities, factors, strict=True)]


class RiskEngine:
    """Stateless deterministic risk calculator."""

    version = "1.0"

    def calculate(self, data: RiskInput) -> RiskResult:
        sev_w = level_weight(data.event_severity)
        crit_w = level_weight(data.origin_criticality)
        strongest = max_level([str(s) for s in data.dependency_strengths])
        dep_w = level_weight(strongest)
        infra_ws = _weighted(data.affected_infrastructure_criticalities, data.affected_infrastructure_impact)
        svc_ws = _weighted(data.affected_service_criticalities, data.affected_service_impact)
        infra_ratio = _saturating(infra_ws, INFRASTRUCTURE_SATURATION)
        svc_ratio = _saturating(svc_ws, SERVICE_SATURATION)

        factors = (
            RiskFactor(
                name="event_severity",
                input=str(data.event_severity),
                weight=sev_w,
                max_points=FACTOR_MAX_POINTS["event_severity"],
                points=sev_w * FACTOR_MAX_POINTS["event_severity"],
                description=f"{data.event_severity} severity event",
            ),
            RiskFactor(
                name="infrastructure_criticality",
                input=str(data.origin_criticality) if data.origin_criticality else None,
                weight=crit_w,
                max_points=FACTOR_MAX_POINTS["infrastructure_criticality"],
                points=crit_w * FACTOR_MAX_POINTS["infrastructure_criticality"],
                description=(
                    f"origin asset criticality {data.origin_criticality}"
                    if data.origin_criticality
                    else "no origin asset identified"
                ),
            ),
            RiskFactor(
                name="dependency_strength",
                input=strongest,
                weight=dep_w,
                max_points=FACTOR_MAX_POINTS["dependency_strength"],
                points=dep_w * FACTOR_MAX_POINTS["dependency_strength"],
                description=(f"strongest cascading dependency is {strongest}" if strongest else "no dependent assets"),
            ),
            RiskFactor(
                name="affected_infrastructure",
                input=len(infra_ws),
                weight=infra_ratio,
                max_points=FACTOR_MAX_POINTS["affected_infrastructure"],
                points=infra_ratio * FACTOR_MAX_POINTS["affected_infrastructure"],
                description=f"{len(infra_ws)} downstream infrastructure asset(s) affected",
            ),
            RiskFactor(
                name="affected_services",
                input=len(svc_ws),
                weight=svc_ratio,
                max_points=FACTOR_MAX_POINTS["affected_services"],
                points=svc_ratio * FACTOR_MAX_POINTS["affected_services"],
                description=f"{len(svc_ws)} public service(s) affected",
            ),
        )

        score = int(clamp(round_half_up(sum(f.points for f in factors)), 0, 100))
        level = level_for_score(score)

        impact_points = sum(
            f.points
            for f in factors
            if f.name in {"infrastructure_criticality", "affected_infrastructure", "affected_services"}
        )
        impact_max = (
            FACTOR_MAX_POINTS["infrastructure_criticality"]
            + FACTOR_MAX_POINTS["affected_infrastructure"]
            + FACTOR_MAX_POINTS["affected_services"]
        )
        impact_score = round_half_up(100 * impact_points / impact_max)
        likelihood_score = round_half_up(100 * (0.7 * sev_w + 0.3 * dep_w))

        critical_services = sum(1 for c in data.affected_service_criticalities if c == "CRITICAL")
        explanation = self._explain(
            data=data,
            score=score,
            level=level,
            strongest=strongest,
            infra_count=len(infra_ws),
            svc_count=len(svc_ws),
            critical_services=critical_services,
            factors=factors,
        )
        return RiskResult(
            score=score,
            level=level,
            impact_score=int(clamp(impact_score, 0, 100)),
            likelihood_score=int(clamp(likelihood_score, 0, 100)),
            affected_infrastructure_count=len(infra_ws),
            affected_services_count=len(svc_ws),
            explanation=explanation,
            factors=factors,
        )

    @staticmethod
    def _explain(
        *,
        data: RiskInput,
        score: int,
        level: str,
        strongest: str | None,
        infra_count: int,
        svc_count: int,
        critical_services: int,
        factors: tuple[RiskFactor, ...],
    ) -> str:
        event_label = f"{data.event_severity} severity {data.event_type or 'event'}"
        origin = (
            f" on {data.origin_criticality} infrastructure '{data.origin_name}'"
            if data.origin_name and data.origin_criticality
            else ""
        )
        cascade = (
            f"; cascades via {strongest} dependencies to {infra_count} infrastructure asset(s) "
            f"and {svc_count} public service(s) ({critical_services} critical)"
            if strongest or infra_count or svc_count
            else "; no downstream dependencies affected"
        )
        top = sorted(factors, key=lambda f: (-f.points, f.name))[:2]
        drivers = ", ".join(f"{f.name} ({f.points:.1f}/{f.max_points:.0f})" for f in top)
        return f"Risk is {level} ({score}/100): {event_label}{origin}{cascade}. Main drivers: {drivers}."


def match_recommendation_rules(
    *,
    event_type: str,
    risk_level: str,
    affected_infrastructure_types: Iterable[str],
    affected_service_types: Iterable[str],
    rules: Sequence[RecommendationRule] = RECOMMENDATION_RULES,
) -> list[RecommendationRule]:
    """Return matching rules, most urgent first, in a deterministic order.

    ``Continue monitoring`` is only returned when nothing else matched.
    """
    infra_types = set(map(str, affected_infrastructure_types))
    svc_types = set(map(str, affected_service_types))
    rank = _LEVEL_RANK.get(str(risk_level), 0)

    matched: list[RecommendationRule] = []
    for rule in rules:
        if rule.key == "monitor":
            continue
        if rank < _LEVEL_RANK[rule.min_risk_level]:
            continue
        if rule.event_types and str(event_type) not in rule.event_types:
            continue
        if rule.affected_infrastructure_types and not infra_types & set(rule.affected_infrastructure_types):
            continue
        if rule.affected_service_types and not svc_types & set(rule.affected_service_types):
            continue
        matched.append(rule)

    if not matched:
        matched = [r for r in rules if r.key == "monitor"]
    order = {r.key: i for i, r in enumerate(rules)}
    return sorted(matched, key=lambda r: (-_LEVEL_RANK[r.priority], order[r.key]))
