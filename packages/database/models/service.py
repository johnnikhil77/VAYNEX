from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from packages.common.enums import Criticality, ServiceStatus, ServiceType
from packages.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from packages.database.types import str_enum


class PublicService(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A public service (e.g. Emergency Healthcare) delivered by an organisation."""

    __tablename__ = "services"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    service_type: Mapped[ServiceType] = mapped_column(str_enum(ServiceType), nullable=False, index=True)
    status: Mapped[ServiceStatus] = mapped_column(
        str_enum(ServiceStatus), nullable=False, default=ServiceStatus.OPERATIONAL, index=True
    )
    criticality: Mapped[Criticality] = mapped_column(
        str_enum(Criticality), nullable=False, default=Criticality.MEDIUM, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    infrastructure_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("infrastructure.id", ondelete="SET NULL"), nullable=True, index=True
    )
