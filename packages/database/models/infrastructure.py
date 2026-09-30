from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from packages.common.enums import Criticality, InfrastructureStatus, InfrastructureType
from packages.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from packages.database.types import JSONBType, PointGeometry, str_enum


class Infrastructure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "infrastructure"
    __table_args__ = (Index("ix_infrastructure_location", "location", postgresql_using="gist"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    infrastructure_type: Mapped[InfrastructureType] = mapped_column(
        str_enum(InfrastructureType), nullable=False, index=True
    )
    status: Mapped[InfrastructureStatus] = mapped_column(
        str_enum(InfrastructureStatus), nullable=False, default=InfrastructureStatus.OPERATIONAL, index=True
    )
    criticality: Mapped[Criticality] = mapped_column(
        str_enum(Criticality), nullable=False, default=Criticality.MEDIUM, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    # PostGIS POINT (SRID 4326), kept in sync with latitude/longitude.
    location: Mapped[Any | None] = mapped_column(PointGeometry, nullable=True)
    # "metadata" is reserved by SQLAlchemy's declarative API -> attribute "meta".
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONBType, nullable=False, default=dict, server_default="{}"
    )
