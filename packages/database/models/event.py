from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from packages.common.enums import EventType, Severity
from packages.common.utils import utcnow
from packages.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from packages.database.types import JSONBType, PointGeometry, str_enum


class Event(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_location", "location", postgresql_using="gist"),)

    event_type: Mapped[EventType] = mapped_column(str_enum(EventType), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[Severity] = mapped_column(str_enum(Severity), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    infrastructure_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("infrastructure.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[Any | None] = mapped_column(PointGeometry, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False, default=dict, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
