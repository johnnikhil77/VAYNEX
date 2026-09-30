"""AI provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from packages.intelligence.schemas import AIAnalysis, IncidentContext


class AIProvider(ABC):
    """Analyse an incident and return advisory, human-reviewable output.

    Implementations must never trigger actions on physical infrastructure.
    """

    name: str = "abstract"
    model: str | None = None

    @abstractmethod
    async def analyze_incident(self, context: IncidentContext) -> AIAnalysis:
        """Return an ``AIAnalysis`` for the incident described by ``context``."""

    def describe(self) -> dict[str, str | None]:
        return {"provider": self.name, "model": self.model}
