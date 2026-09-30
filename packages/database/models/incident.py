from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from packages.common.enums import IncidentStatus, Severity
from packages.common.utils import utcnow
from packages.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from packages.database.types import JSONBType, str_enum


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incidents"

    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        str_enum(IncidentStatus), nullable=False, default=IncidentStatus.OPEN, index=True
    )
    severity: Mapped[Severity] = mapped_column(str_enum(Severity), nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Snapshot of the impact analysis at detection time (list of affected nodes
    # with depth, path and previous status) - preserved for audit/replay.
    affected_infrastructure: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBType, nullable=False, default=list, server_default="[]"
    )
    affected_services: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBType, nullable=False, default=list, server_default="[]"
    )
    # Latest AI analysis (summary, impact, actions, reasoning, confidence).
    ai_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONBType, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
