from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from packages.common.enums import RecommendationPriority, RecommendationSource, RecommendationStatus
from packages.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from packages.database.types import str_enum


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[RecommendationPriority] = mapped_column(
        str_enum(RecommendationPriority), nullable=False, index=True
    )
    source: Mapped[RecommendationSource] = mapped_column(str_enum(RecommendationSource), nullable=False, index=True)
    status: Mapped[RecommendationStatus] = mapped_column(
        str_enum(RecommendationStatus), nullable=False, default=RecommendationStatus.PENDING, index=True
    )
    rule_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Human decision trail
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
