"""Deterministic, offline AI provider.

Produces realistic, context-aware analysis from templates so the prototype
works without any external API key. Same context in -> same analysis out.
"""

from __future__ import annotations

from packages.intelligence.interface import AIProvider
from packages.intelligence.schemas import AIAnalysis, AIRecommendedAction, ContextAsset, IncidentContext

_EVENT_LABELS: dict[str, str] = {
    "POWER_FAILURE": "power failure",
    "WATER_DISRUPTION": "water supply disruption",
    "TELECOM_OUTAGE": "telecommunications outage",
    "FLOOD": "flood event",
    "EQUIPMENT_FAILURE": "equipment failure",
    "CYBER_INCIDENT": "cyber incident",
    "FIRE": "fire",
    "EARTHQUAKE": "earthquake",
    "TRAFFIC_DISRUPTION": "traffic disruption",
    "SENSOR_ALERT": "sensor alert",
}

_ASSET_IMPACT: dict[str, str] = {
    "HOSPITAL": "{name}: clinical capacity at risk; ICU, operating theatres and life-support rely on backup systems",
    "POWER_SUBSTATION": "{name}: loss of supply to downstream feeders and dependent facilities",
    "POWER_PLANT": "{name}: generation shortfall may trigger load shedding across the grid",
    "WATER_TREATMENT": "{name}: treated-water output reduced; pressure loss expected in the distribution network",
    "WATER_PIPELINE": "{name}: pressure loss and possible contamination risk downstream",
    "TELECOM_TOWER": "{name}: mobile and data coverage loss in the surrounding cells",
    "EMERGENCY_CENTER": "{name}: dispatch and coordination capability degraded",
    "ROAD": "{name}: access routes for ambulances and response vehicles obstructed",
    "BRIDGE": "{name}: crossing capacity reduced; detours increase response times",
    "SCHOOL": "{name}: occupant safety and continuity of classes affected",
    "DATA_CENTER": "{name}: hosted digital public services may become unavailable",
}

_SERVICE_IMPACT: dict[str, str] = {
    "EMERGENCY_HEALTHCARE": "{name}: emergency admissions may need diversion; time-critical care delayed",
    "HEALTHCARE": "{name}: elective procedures likely postponed",
    "POWER_SUPPLY": "{name}: customers in the affected feeder zone without electricity",
    "WATER_SUPPLY": "{name}: households and facilities face supply interruption",
    "TELECOMMUNICATIONS": "{name}: voice and data connectivity degraded for citizens and agencies",
    "EMERGENCY_COMMUNICATIONS": "{name}: first-responder coordination at risk",
    "EMERGENCY_RESPONSE": "{name}: response times likely to increase",
    "TRANSPORTATION": "{name}: congestion and restricted mobility in the corridor",
}

_EVENT_ACTIONS: dict[str, list[tuple[str, str]]] = {
    "POWER_FAILURE": [
        (
            "Prioritise feeder restoration for {critical}",
            "Recommend the grid operator restores feeders supplying {critical} first and "
            "confirms estimated restoration time.",
        ),
        (
            "Verify generator transfer and fuel at {critical}",
            "Ask facility engineering to confirm automatic transfer switch operation, generator "
            "load and fuel autonomy; report back within 15 minutes.",
        ),
        (
            "Pre-alert neighbouring facilities for patient transfer",
            "Place nearby hospitals on standby to receive critical patients if backup power "
            "autonomy drops below 4 hours.",
        ),
    ],
    "WATER_DISRUPTION": [
        (
            "Prioritise water allocation to {critical}",
            "Recommend reserving remaining storage and tanker capacity for {critical}.",
        ),
        (
            "Confirm on-site water storage levels",
            "Ask affected facilities to report storage autonomy in hours and activate conservation plans.",
        ),
        (
            "Coordinate boil-water advisory readiness",
            "Prepare a precautionary advisory in case treatment quality cannot be assured on restart.",
        ),
    ],
    "TELECOM_OUTAGE": [
        (
            "Switch {critical} to fallback channels",
            "Recommend moving emergency coordination for {critical} to radio / satellite fallback.",
        ),
        (
            "Confirm reachability of hospitals and field units",
            "Run a roll-call over fallback channels to confirm every critical site is reachable.",
        ),
        (
            "Request carrier root-cause and ETA",
            "Ask the telecom operator for root cause, affected cells and restoration estimate.",
        ),
    ],
    "FLOOD": [
        (
            "Protect access to {critical}",
            "Recommend sandbagging and pumping around {critical} and keep at least one access route open.",
        ),
        (
            "Pre-emptively secure electrical equipment",
            "Advise utilities to assess de-energising flood-exposed equipment to prevent damage and "
            "electrocution risk.",
        ),
        (
            "Stage evacuation support",
            "Prepare evacuation transport for vulnerable patients and residents in low-lying zones.",
        ),
    ],
}

_DEFAULT_ACTIONS: list[tuple[str, str]] = [
    (
        "Assess condition of {critical}",
        "Request an on-site inspection of {critical} and confirm operational status.",
    ),
    (
        "Confirm status with dependent service owners",
        "Contact owners of dependent services to confirm impact and contingency readiness.",
    ),
]

_PRIORITY_BY_LEVEL = {
    "CRITICAL": ["CRITICAL", "HIGH", "HIGH"],
    "HIGH": ["HIGH", "HIGH", "MEDIUM"],
    "MEDIUM": ["MEDIUM", "MEDIUM", "LOW"],
    "LOW": ["LOW", "LOW", "LOW"],
}


def _humanize(value: str) -> str:
    return value.replace("_", " ").lower()


def _rank(assets: list[ContextAsset]) -> list[ContextAsset]:
    crit = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
    return sorted(assets, key=lambda a: (-a.impact_weight, -crit.get(a.criticality, 0), a.name))


class MockAIProvider(AIProvider):
    name = "mock"
    model = "vaynex-mock-analyst-v1"

    async def analyze_incident(self, context: IncidentContext) -> AIAnalysis:
        return self.build_analysis(context)

    def build_analysis(self, context: IncidentContext) -> AIAnalysis:
        label = _EVENT_LABELS.get(context.event_type, _humanize(context.event_type))
        infra = _rank(list(context.affected_infrastructure))
        services = _rank(list(context.affected_services))
        critical_services = [s.name for s in services if s.criticality == "CRITICAL"]

        origin_text = f" at {context.origin.name} ({_humanize(context.origin.type)})" if context.origin else ""
        summary = (
            f"{context.severity.capitalize()} severity {label}{origin_text} is cascading to "
            f"{len(infra)} dependent infrastructure asset(s) and {len(services)} public service(s). "
            f"Assessed risk is {context.risk.level} ({context.risk.score}/100)."
        )
        if critical_services:
            summary += f" Critical services at risk: {', '.join(critical_services[:4])}."

        impacts: list[str] = []
        if context.origin:
            tmpl = _ASSET_IMPACT.get(context.origin.type, "{name}: operational disruption reported")
            impacts.append(tmpl.format(name=context.origin.name))
        for asset in infra[:4]:
            tmpl = _ASSET_IMPACT.get(asset.type, "{name}: dependent operations disrupted")
            impacts.append(tmpl.format(name=asset.name))
        for svc in services[:4]:
            tmpl = _SERVICE_IMPACT.get(svc.type, "{name}: service continuity at risk")
            impacts.append(tmpl.format(name=svc.name))
        duration = context.payload.get("duration_minutes")
        if isinstance(duration, int | float) and duration > 0:
            impacts.append(
                f"Disruption has lasted {int(duration)} minutes; backup autonomy becomes the limiting factor."
            )

        focus_candidates = [a for a in infra if a.criticality == "CRITICAL"] or infra or services
        critical_name = (
            focus_candidates[0].name
            if focus_candidates
            else (context.origin.name if context.origin else "the affected site")
        )
        templates = _EVENT_ACTIONS.get(context.event_type, _DEFAULT_ACTIONS)
        priorities = _PRIORITY_BY_LEVEL.get(context.risk.level, _PRIORITY_BY_LEVEL["MEDIUM"])
        actions = [
            AIRecommendedAction(
                title=title.format(critical=critical_name),
                description=desc.format(critical=critical_name),
                priority=priorities[min(i, len(priorities) - 1)],
            )
            for i, (title, desc) in enumerate(templates)
        ]

        path_hint = ""
        if infra:
            top = infra[0]
            path_hint = (
                f" The highest-impact downstream asset is {top.name} (depth {top.depth}, "
                f"impact weight {top.impact_weight:.2f})."
            )
        reasoning = (
            f"Analysis derived from the Vaynex dependency graph and deterministic risk model. "
            f"The {label} affects {len(infra) + len(services)} downstream node(s).{path_hint} "
            f"Risk engine: {context.risk.explanation} "
            "Recommendations are advisory and require operator approval."
        ).strip()

        confidence = 0.72 + 0.04 * min(len(infra) + len(services), 4)
        confidence += 0.03 if context.origin else 0.0
        confidence += 0.02 if context.risk.level == "CRITICAL" else 0.0
        confidence = round(min(confidence, 0.95), 2)

        return AIAnalysis(
            summary=summary,
            potential_impact=impacts,
            affected_services=[s.name for s in services],
            recommended_actions=actions,
            reasoning=reasoning,
            confidence=confidence,
            provider=self.name,
            model=self.model,
        )
