from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from packages.common.enums import DependencyStrength, DependencyType
from packages.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from packages.database.types import str_enum


class Dependency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Directed edge: the *target* depends on the *source*.

    Example: source=Central Power Substation -> target=Hyderabad Central Hospital
    means the hospital depends on the substation for power.
    Exactly one source column and exactly one target column must be set.
    """

    __tablename__ = "dependencies"
    __table_args__ = (
        CheckConstraint("num_nonnulls(source_infrastructure_id, source_service_id) = 1", name="one_source"),
        CheckConstraint("num_nonnulls(target_infrastructure_id, target_service_id) = 1", name="one_target"),
    )

    source_infrastructure_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("infrastructure.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )
    target_infrastructure_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("infrastructure.id", ondelete="CASCADE"), nullable=True, index=True
    )
    target_service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )
    dependency_type: Mapped[DependencyType] = mapped_column(str_enum(DependencyType), nullable=False, index=True)
    strength: Mapped[DependencyStrength] = mapped_column(
        str_enum(DependencyStrength), nullable=False, default=DependencyStrength.MEDIUM
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
