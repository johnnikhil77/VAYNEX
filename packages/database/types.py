"""Reusable column types."""

from __future__ import annotations

from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB

# Spatial point in WGS84. The GiST index is declared explicitly on each table
# (and in the migration) rather than implicitly by GeoAlchemy2.
PointGeometry = Geometry(geometry_type="POINT", srid=4326, spatial_index=False)

JSONBType = JSONB


def str_enum(enum_cls: type[StrEnum], length: int = 32) -> SAEnum:
    """Store a ``StrEnum`` as VARCHAR (non-native enum -> simple migrations)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=length,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )
