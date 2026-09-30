from __future__ import annotations

from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column

from packages.common.enums import UserRole
from packages.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from packages.database.types import str_enum


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole), nullable=False, default=UserRole.VIEWER, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    def __repr__(self) -> str:  # never include the password hash
        return f"User(id={self.id!s}, email={self.email!r}, role={self.role})"
