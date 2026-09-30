"""Provider-neutral input/output contracts for AI incident analysis."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContextAsset(BaseModel):
    """An affected infrastructure asset or public service, as seen by the AI."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    kind: str  # INFRASTRUCTURE | SERVICE
    type: str
    criticality: str
    relationship: str = "DEPENDENCY"
    depth: int = 1
    impact_weight: float = 1.0


class ContextRisk(BaseModel):
    score: int
    level: str
    explanation: str = ""


class IncidentContext(BaseModel):
    """Everything an AI provider may know about an incident.

    Only operational metadata is included: no user data, no credentials.
    """

    incident_id: str
    title: str
    description: str = ""
    event_type: str
    severity: str
    source: str = "unknown"
    origin: ContextAsset | None = None
    affected_infrastructure: list[ContextAsset] = Field(default_factory=list)
    affected_services: list[ContextAsset] = Field(default_factory=list)
    risk: ContextRisk
    payload: dict[str, Any] = Field(default_factory=dict)


class AIRecommendedAction(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    priority: str = "MEDIUM"

    @field_validator("priority")
    @classmethod
    def _normalise_priority(cls, value: str) -> str:
        value = str(value).upper()
        return value if value in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "MEDIUM"


class AIAnalysis(BaseModel):
    summary: str
    potential_impact: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    recommended_actions: list[AIRecommendedAction] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    provider: str = "mock"
    model: str | None = None
    advisory_only: bool = True
