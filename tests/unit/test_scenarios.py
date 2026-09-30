"""Scenario catalogue + in-memory dependency propagation (no database)."""

from __future__ import annotations

import uuid

from apps.api.services import demo_data
from apps.api.services.dependency_service import ImpactOrigin, build_graph, propagate_impact, split_by_kind
from apps.api.services.incident_service import should_create_incident, target_status
from apps.api.services.simulation_service import SCENARIOS, list_scenarios
from packages.common.enums import EntityKind, ImpactRelationship, SimulationScenario
from packages.database.models import Dependency, Infrastructure, PublicService
from packages.risk import RiskEngine, RiskInput


def _demo_graph():
    """Build the Hyderabad demo graph from the seed specification, in memory."""
    orgs = {spec["name"]: uuid.uuid4() for spec in demo_data.ORGANIZATIONS}
    infra = {
        spec["name"]: Infrastructure(
            id=uuid.uuid4(),
            organization_id=orgs[spec["org"]],
            name=spec["name"],
            infrastructure_type=spec["infrastructure_type"],
            criticality=spec["criticality"],
            status="OPERATIONAL",
            latitude=spec["latitude"],
            longitude=spec["longitude"],
        )
        for spec in demo_data.INFRASTRUCTURE
    }
    services = {
        spec["name"]: PublicService(
            id=uuid.uuid4(),
            organization_id=orgs[spec["org"]],
            name=spec["name"],
            service_type=spec["service_type"],
            criticality=spec["criticality"],
            status="OPERATIONAL",
            infrastructure_id=infra[spec["infra"]].id,
        )
        for spec in demo_data.SERVICES
    }
    deps = []
    for s_kind, s_name, t_kind, t_name, dep_type, strength, _ in demo_data.DEPENDENCIES:
        dep = Dependency(id=uuid.uuid4(), dependency_type=dep_type, strength=strength)
        if s_kind == "I":
            dep.source_infrastructure_id = infra[s_name].id
        else:
            dep.source_service_id = services[s_name].id
        if t_kind == "I":
            dep.target_infrastructure_id = infra[t_name].id
        else:
            dep.target_service_id = services[t_name].id
        deps.append(dep)
    return build_graph(list(infra.values()), list(services.values()), deps), infra, services


def test_all_four_scenarios_are_defined_with_existing_origins() -> None:
    assert set(SCENARIOS) == set(SimulationScenario)
    infra_names = {spec["name"] for spec in demo_data.INFRASTRUCTURE}
    service_names = {spec["name"] for spec in demo_data.SERVICES}
    for scenario in SCENARIOS.values():
        assert scenario.origin in infra_names
        assert set(scenario.chain) <= infra_names | service_names
    assert [s.key.value for s in list_scenarios()] == [
        "hospital_power_failure",
        "water_supply_disruption",
        "telecom_outage",
        "flood_infrastructure_risk",
    ]


def test_hospital_power_failure_cascades_to_emergency_healthcare() -> None:
    graph, infra, _ = _demo_graph()
    origin = infra["Central Power Substation"]
    impact = propagate_impact(graph, [ImpactOrigin(key=(EntityKind.INFRASTRUCTURE, origin.id))])
    affected_infra, affected_services = split_by_kind(impact)
    by_name = {i["name"]: i for i in impact}

    assert affected_infra[0]["name"] == "Central Power Substation"
    assert affected_infra[0]["relationship"] == ImpactRelationship.ORIGIN
    hospital = by_name["Hyderabad Central Hospital"]
    assert hospital["depth"] == 1 and hospital["impact_weight"] == 1.0
    healthcare = by_name["Emergency Healthcare"]
    assert healthcare["path"] == ["Central Power Substation", "Hyderabad Central Hospital", "Emergency Healthcare"]
    # telecom is not powered by this substation in the demo topology
    assert "Telecommunications" not in by_name
    # deterministic
    assert propagate_impact(graph, [ImpactOrigin(key=(EntityKind.INFRASTRUCTURE, origin.id))]) == impact
    assert {s["name"] for s in affected_services} >= {"Emergency Healthcare", "Electricity Distribution"}


def test_propagation_respects_minimum_weight_threshold() -> None:
    graph, infra, _ = _demo_graph()
    impact = propagate_impact(
        graph, [ImpactOrigin(key=(EntityKind.INFRASTRUCTURE, infra["Central Power Substation"].id))]
    )
    assert all(i["impact_weight"] >= 0.25 for i in impact)
    water = next(i for i in impact if i["name"] == "Water Supply Service")
    assert water["impact_weight"] == 0.5  # substation -MEDIUM-> plant -CRITICAL-> service


def test_telecom_outage_chain() -> None:
    graph, infra, _ = _demo_graph()
    impact = propagate_impact(graph, [ImpactOrigin(key=(EntityKind.INFRASTRUCTURE, infra["Telecom Tower"].id))])
    names = [i["name"] for i in impact]
    assert names.index("Telecommunications") < names.index("Emergency Communications")
    assert "Hyderabad Central Hospital" not in names


def test_hospital_scenario_scores_critical_risk() -> None:
    graph, infra, _ = _demo_graph()
    impact = propagate_impact(
        graph, [ImpactOrigin(key=(EntityKind.INFRASTRUCTURE, infra["Central Power Substation"].id))]
    )
    downstream = [i for i in impact if i["relationship"] != "ORIGIN"]
    infra_d = [i for i in downstream if i["kind"] == "INFRASTRUCTURE"]
    svc_d = [i for i in downstream if i["kind"] == "SERVICE"]
    result = RiskEngine().calculate(
        RiskInput(
            event_severity="CRITICAL",
            origin_criticality="CRITICAL",
            dependency_strengths=tuple(i["dependency_strength"] for i in downstream),
            affected_infrastructure_criticalities=tuple(i["criticality"] for i in infra_d),
            affected_service_criticalities=tuple(i["criticality"] for i in svc_d),
            affected_infrastructure_impact=tuple(i["impact_weight"] for i in infra_d),
            affected_service_impact=tuple(i["impact_weight"] for i in svc_d),
        )
    )
    assert result.level == "CRITICAL"
    assert 80 <= result.score <= 100


def test_incident_detection_and_status_rules() -> None:
    origin = {"relationship": "ORIGIN", "criticality": "LOW", "kind": "INFRASTRUCTURE", "impact_weight": 1.0}
    assert not should_create_incident("LOW", [origin])
    assert should_create_incident("MEDIUM", [origin])
    assert should_create_incident("LOW", [{**origin, "criticality": "HIGH"}])
    assert target_status(origin, "CRITICAL") == "FAILED"
    assert target_status(origin, "MEDIUM") == "DEGRADED"
    svc = {"relationship": "DEPENDENCY", "kind": "SERVICE", "impact_weight": 0.3}
    assert target_status(svc, "CRITICAL") is None
    assert target_status({**svc, "impact_weight": 0.8}, "HIGH") == "DISRUPTED"
