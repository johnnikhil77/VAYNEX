from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.common.enums import OrganizationType
from packages.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from packages.database.types import str_enum


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    organization_type: Mapped[OrganizationType] = mapped_column(str_enum(OrganizationType), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
