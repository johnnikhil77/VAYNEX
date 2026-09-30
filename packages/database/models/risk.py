from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from packages.common.enums import RiskLevel
from packages.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from packages.database.types import JSONBType, str_enum


class RiskAssessment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A risk calculation for an incident. Recalculations append new rows."""

    __tablename__ = "risks"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[RiskLevel] = mapped_column(str_enum(RiskLevel), nullable=False, index=True)
    impact_score: Mapped[int] = mapped_column(Integer, nullable=False)
    likelihood_score: Mapped[int] = mapped_column(Integer, nullable=False)
    affected_services_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    affected_infrastructure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONBType, nullable=False, default=list, server_default="[]")
