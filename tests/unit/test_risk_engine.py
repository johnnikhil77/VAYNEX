"""Deterministic risk engine tests."""

from __future__ import annotations

import pytest

from packages.risk import RiskEngine, RiskInput, level_for_score, match_recommendation_rules

engine = RiskEngine()


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, "LOW"),
        (29, "LOW"),
        (30, "MEDIUM"),
        (59, "MEDIUM"),
        (60, "HIGH"),
        (79, "HIGH"),
        (80, "CRITICAL"),
        (100, "CRITICAL"),
    ],
)
def test_level_thresholds(score: int, level: str) -> None:
    assert level_for_score(score) == level


def test_same_input_produces_identical_result() -> None:
    data = RiskInput(
        event_severity="HIGH",
        origin_criticality="CRITICAL",
        dependency_strengths=("HIGH", "CRITICAL"),
        affected_infrastructure_criticalities=("CRITICAL", "HIGH"),
        affected_service_criticalities=("CRITICAL", "MEDIUM"),
        event_type="POWER_FAILURE",
        origin_name="Central Power Substation",
    )
    results = {engine.calculate(data) for _ in range(5)}
    assert len(results) == 1


def test_minimal_event_is_low_risk() -> None:
    result = engine.calculate(RiskInput(event_severity="LOW", origin_criticality="LOW"))
    assert result.level == "LOW"
    assert result.score == 13  # 6.25 + 6.25 rounded half-up
    assert result.affected_services_count == 0


def test_maximal_cascade_is_critical_and_capped_at_100() -> None:
    result = engine.calculate(
        RiskInput(
            event_severity="CRITICAL",
            origin_criticality="CRITICAL",
            dependency_strengths=("CRITICAL",),
            affected_infrastructure_criticalities=("CRITICAL",) * 10,
            affected_service_criticalities=("CRITICAL",) * 10,
        )
    )
    assert result.score == 100
    assert result.level == "CRITICAL"
    assert result.impact_score == 100
    assert result.likelihood_score == 100


def test_each_factor_increases_score_monotonically() -> None:
    base = RiskInput(event_severity="MEDIUM", origin_criticality="MEDIUM")
    s0 = engine.calculate(base).score
    s1 = engine.calculate(RiskInput(event_severity="HIGH", origin_criticality="MEDIUM")).score
    s2 = engine.calculate(
        RiskInput(event_severity="MEDIUM", origin_criticality="MEDIUM", dependency_strengths=("HIGH",))
    ).score
    s3 = engine.calculate(
        RiskInput(event_severity="MEDIUM", origin_criticality="MEDIUM", affected_service_criticalities=("CRITICAL",))
    ).score
    assert s1 > s0 and s2 > s0 and s3 > s0


def test_impact_weights_reduce_contribution_of_distant_nodes() -> None:
    near = RiskInput(event_severity="HIGH", affected_service_criticalities=("CRITICAL", "CRITICAL"))
    far = RiskInput(
        event_severity="HIGH",
        affected_service_criticalities=("CRITICAL", "CRITICAL"),
        affected_service_impact=(0.25, 0.25),
    )
    assert engine.calculate(far).score < engine.calculate(near).score
    with pytest.raises(ValueError):
        engine.calculate(
            RiskInput(event_severity="HIGH", affected_service_criticalities=("LOW",), affected_service_impact=(1, 1))
        )


def test_result_exposes_explainable_factors() -> None:
    result = engine.calculate(
        RiskInput(
            event_severity="CRITICAL",
            origin_criticality="CRITICAL",
            origin_name="Substation",
            event_type="POWER_FAILURE",
            dependency_strengths=("CRITICAL",),
            affected_infrastructure_criticalities=("CRITICAL",),
            affected_service_criticalities=("CRITICAL",),
        )
    )
    names = [f["name"] for f in result.factors_as_dicts()]
    assert names == [
        "event_severity",
        "infrastructure_criticality",
        "dependency_strength",
        "affected_infrastructure",
        "affected_services",
    ]
    assert round(sum(f["points"] for f in result.factors_as_dicts())) == result.score
    assert "Substation" in result.explanation and result.level in result.explanation


def test_recommendation_rules_match_power_failure_at_hospital() -> None:
    rules = match_recommendation_rules(
        event_type="POWER_FAILURE",
        risk_level="CRITICAL",
        affected_infrastructure_types=["POWER_SUBSTATION", "HOSPITAL"],
        affected_service_types=["EMERGENCY_HEALTHCARE"],
    )
    keys = [r.key for r in rules]
    assert keys[0] == "activate_backup_power"
    assert {"divert_ambulances", "dispatch_grid_crew", "public_advisory"} <= set(keys)
    assert "deploy_mobile_cell" not in keys
    priorities = [r.priority for r in rules]
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    assert priorities == sorted(priorities, key=order.__getitem__)


def test_low_risk_without_matches_falls_back_to_monitoring() -> None:
    rules = match_recommendation_rules(
        event_type="SENSOR_ALERT", risk_level="LOW", affected_infrastructure_types=[], affected_service_types=[]
    )
    assert [r.key for r in rules] == ["monitor"]
