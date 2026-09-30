"""Initial Vaynex schema (PostGIS enabled).

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
TS = sa.DateTime(timezone=True)


def _enum() -> sa.String:
    # Enums are stored as VARCHAR(32) (non-native) and validated by the app.
    return sa.String(length=32)


def _point() -> Geometry:
    return Geometry(geometry_type="POINT", srid=4326, spatial_index=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # users ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", UUID, nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", _enum(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    # organizations ----------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", UUID, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("organization_type", _enum(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
    )
    op.create_index("ix_organizations_organization_type", "organizations", ["organization_type"])

    # infrastructure ---------------------------------------------------------
    op.create_table(
        "infrastructure",
        sa.Column("id", UUID, nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("infrastructure_type", _enum(), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("criticality", _enum(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("location", _point(), nullable=True),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_infrastructure"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_infrastructure_organization_id_organizations",
            ondelete="CASCADE",
        ),
    )
    for col in ("organization_id", "name", "infrastructure_type", "status", "criticality"):
        op.create_index(f"ix_infrastructure_{col}", "infrastructure", [col])
    op.create_index("ix_infrastructure_location", "infrastructure", ["location"], postgresql_using="gist")

    # services ---------------------------------------------------------------
    op.create_table(
        "services",
        sa.Column("id", UUID, nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("service_type", _enum(), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("criticality", _enum(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("infrastructure_id", UUID, nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_services"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_services_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["infrastructure_id"],
            ["infrastructure.id"],
            name="fk_services_infrastructure_id_infrastructure",
            ondelete="SET NULL",
        ),
    )
    for col in ("organization_id", "name", "service_type", "status", "criticality", "infrastructure_id"):
        op.create_index(f"ix_services_{col}", "services", [col])

    # dependencies -----------------------------------------------------------
    op.create_table(
        "dependencies",
        sa.Column("id", UUID, nullable=False),
        sa.Column("source_infrastructure_id", UUID, nullable=True),
        sa.Column("source_service_id", UUID, nullable=True),
        sa.Column("target_infrastructure_id", UUID, nullable=True),
        sa.Column("target_service_id", UUID, nullable=True),
        sa.Column("dependency_type", _enum(), nullable=False),
        sa.Column("strength", _enum(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_dependencies"),
        sa.CheckConstraint(
            "num_nonnulls(source_infrastructure_id, source_service_id) = 1",
            name="ck_dependencies_one_source",
        ),
        sa.CheckConstraint(
            "num_nonnulls(target_infrastructure_id, target_service_id) = 1",
            name="ck_dependencies_one_target",
        ),
        sa.ForeignKeyConstraint(
            ["source_infrastructure_id"],
            ["infrastructure.id"],
            name="fk_dependencies_source_infrastructure_id_infrastructure",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_service_id"],
            ["services.id"],
            name="fk_dependencies_source_service_id_services",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_infrastructure_id"],
            ["infrastructure.id"],
            name="fk_dependencies_target_infrastructure_id_infrastructure",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_service_id"],
            ["services.id"],
            name="fk_dependencies_target_service_id_services",
            ondelete="CASCADE",
        ),
    )
    for col in (
        "source_infrastructure_id",
        "source_service_id",
        "target_infrastructure_id",
        "target_service_id",
        "dependency_type",
    ):
        op.create_index(f"ix_dependencies_{col}", "dependencies", [col])

    # events -----------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", UUID, nullable=False),
        sa.Column("event_type", _enum(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("severity", _enum(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("infrastructure_id", UUID, nullable=True),
        sa.Column("service_id", UUID, nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("location", _point(), nullable=True),
        sa.Column("payload", JSONB, server_default="{}", nullable=False),
        sa.Column("occurred_at", TS, nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
        sa.ForeignKeyConstraint(
            ["infrastructure_id"],
            ["infrastructure.id"],
            name="fk_events_infrastructure_id_infrastructure",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], name="fk_events_service_id_services", ondelete="SET NULL"
        ),
    )
    for col in ("event_type", "severity", "infrastructure_id", "service_id", "occurred_at"):
        op.create_index(f"ix_events_{col}", "events", [col])
    op.create_index("ix_events_location", "events", ["location"], postgresql_using="gist")

    # incidents --------------------------------------------------------------
    op.create_table(
        "incidents",
        sa.Column("id", UUID, nullable=False),
        sa.Column("event_id", UUID, nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("severity", _enum(), nullable=False),
        sa.Column("detected_at", TS, nullable=False),
        sa.Column("resolved_at", TS, nullable=True),
        sa.Column("affected_infrastructure", JSONB, server_default="[]", nullable=False),
        sa.Column("affected_services", JSONB, server_default="[]", nullable=False),
        sa.Column("ai_analysis", JSONB, nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_incidents_event_id_events", ondelete="CASCADE"),
    )
    for col in ("event_id", "status", "severity", "detected_at"):
        op.create_index(f"ix_incidents_{col}", "incidents", [col])

    # risks ------------------------------------------------------------------
    op.create_table(
        "risks",
        sa.Column("id", UUID, nullable=False),
        sa.Column("incident_id", UUID, nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", _enum(), nullable=False),
        sa.Column("impact_score", sa.Integer(), nullable=False),
        sa.Column("likelihood_score", sa.Integer(), nullable=False),
        sa.Column("affected_services_count", sa.Integer(), nullable=False),
        sa.Column("affected_infrastructure_count", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("factors", JSONB, server_default="[]", nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_risks"),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.id"], name="fk_risks_incident_id_incidents", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_risks_incident_id", "risks", ["incident_id"])
    op.create_index("ix_risks_level", "risks", ["level"])

    # recommendations --------------------------------------------------------
    op.create_table(
        "recommendations",
        sa.Column("id", UUID, nullable=False),
        sa.Column("incident_id", UUID, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", _enum(), nullable=False),
        sa.Column("source", _enum(), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("rule_key", sa.String(length=64), nullable=True),
        sa.Column("decided_by", UUID, nullable=True),
        sa.Column("decided_at", TS, nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_recommendations"),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_recommendations_incident_id_incidents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["users.id"], name="fk_recommendations_decided_by_users", ondelete="SET NULL"
        ),
    )
    for col in ("incident_id", "priority", "source", "status"):
        op.create_index(f"ix_recommendations_{col}", "recommendations", [col])

    # audit_logs -------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UUID, nullable=True),
        sa.Column("details", JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_audit_logs_user_id_users", ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    for table in (
        "audit_logs",
        "recommendations",
        "risks",
        "incidents",
        "events",
        "dependencies",
        "services",
        "infrastructure",
        "organizations",
        "users",
    ):
        op.drop_table(table)
    # The postgis extension is intentionally left installed (it may be shared).
