"""AI provider abstraction tests (no network access required)."""

from __future__ import annotations

import json

import httpx
import pytest

from packages.intelligence import (
    AIProvider,
    ContextAsset,
    ContextRisk,
    IncidentContext,
    MockAIProvider,
    OpenAIProvider,
    build_ai_provider,
)

pytestmark = pytest.mark.anyio


def _context() -> IncidentContext:
    return IncidentContext(
        incident_id="00000000-0000-0000-0000-000000000001",
        title="Central Substation Power Failure",
        event_type="POWER_FAILURE",
        severity="CRITICAL",
        origin=ContextAsset(
            id="o",
            name="Central Power Substation",
            kind="INFRASTRUCTURE",
            type="POWER_SUBSTATION",
            criticality="CRITICAL",
            relationship="ORIGIN",
            depth=0,
        ),
        affected_infrastructure=[
            ContextAsset(
                id="h",
                name="Hyderabad Central Hospital",
                kind="INFRASTRUCTURE",
                type="HOSPITAL",
                criticality="CRITICAL",
                depth=1,
                impact_weight=1.0,
            ),
        ],
        affected_services=[
            ContextAsset(
                id="s",
                name="Emergency Healthcare",
                kind="SERVICE",
                type="EMERGENCY_HEALTHCARE",
                criticality="CRITICAL",
                depth=2,
                impact_weight=1.0,
            ),
        ],
        risk=ContextRisk(score=92, level="CRITICAL", explanation="Risk is CRITICAL (92/100)."),
        payload={"duration_minutes": 12},
    )


async def test_mock_provider_is_deterministic_and_complete() -> None:
    provider = MockAIProvider()
    first = await provider.analyze_incident(_context())
    second = await provider.analyze_incident(_context())
    assert first == second
    assert isinstance(provider, AIProvider)
    assert "Central Power Substation" in first.summary and "CRITICAL" in first.summary
    assert first.affected_services == ["Emergency Healthcare"]
    assert any("Hyderabad Central Hospital" in line for line in first.potential_impact)
    assert len(first.recommended_actions) == 3
    assert first.recommended_actions[0].priority == "CRITICAL"
    assert 0.0 < first.confidence <= 0.95
    assert first.advisory_only is True
    assert "advisory" in first.reasoning.lower()


async def test_openai_provider_parses_structured_response() -> None:
    content = {
        "summary": "Substation failure threatens hospital operations.",
        "potential_impact": ["ICU on backup power"],
        "affected_services": ["Emergency Healthcare"],
        "recommended_actions": [
            {"title": "Confirm generator status", "description": "Call facility", "priority": "urgent"}
        ],
        "reasoning": "Hospital depends on substation.",
        "confidence": 1.7,
    }
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})

    provider = OpenAIProvider(api_key="sk-test-key-123456", model="gpt-test", transport=httpx.MockTransport(handler))
    analysis = await provider.analyze_incident(_context())
    assert analysis.provider == "openai" and analysis.model == "gpt-test"
    assert analysis.confidence == 1.0  # clamped
    assert analysis.recommended_actions[0].priority == "MEDIUM"  # unknown priority normalised
    assert seen["auth"] == "Bearer sk-test-key-123456"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert "sk-test" not in repr(provider)


async def test_openai_provider_falls_back_to_mock_on_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    provider = OpenAIProvider(api_key="sk-test-key-123456", transport=httpx.MockTransport(handler))
    analysis = await provider.analyze_incident(_context())
    assert analysis.provider == "mock-fallback"
    assert analysis.summary


def test_provider_selection_defaults_to_mock_without_key() -> None:
    assert isinstance(build_ai_provider(preference="auto", openai_api_key=None), MockAIProvider)
    assert isinstance(build_ai_provider(preference="openai", openai_api_key=""), MockAIProvider)
    assert isinstance(build_ai_provider(preference="mock", openai_api_key="sk-x"), MockAIProvider)
    assert isinstance(build_ai_provider(preference="auto", openai_api_key="sk-x"), OpenAIProvider)
