"""AI intelligence layer: provider abstraction + mock and OpenAI implementations."""

from __future__ import annotations

from packages.intelligence.interface import AIProvider
from packages.intelligence.mock_provider import MockAIProvider
from packages.intelligence.openai_provider import OpenAIProvider
from packages.intelligence.schemas import (
    AIAnalysis,
    AIRecommendedAction,
    ContextAsset,
    ContextRisk,
    IncidentContext,
)


def build_ai_provider(
    *, preference: str = "auto", openai_api_key: str | None = None, openai_model: str = "gpt-4o-mini"
) -> AIProvider:
    """Select a provider.

    ``auto``   -> OpenAI when a key is configured, otherwise the mock provider.
    ``mock``   -> always the deterministic mock provider.
    ``openai`` -> OpenAI (falls back to mock if no key is configured).
    """
    pref = (preference or "auto").lower()
    if pref in {"auto", "openai"} and openai_api_key:
        return OpenAIProvider(api_key=openai_api_key, model=openai_model)
    return MockAIProvider()


__all__ = [
    "AIAnalysis",
    "AIProvider",
    "AIRecommendedAction",
    "ContextAsset",
    "ContextRisk",
    "IncidentContext",
    "MockAIProvider",
    "OpenAIProvider",
    "build_ai_provider",
]
