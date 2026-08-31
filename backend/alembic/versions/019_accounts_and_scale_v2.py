"""Introduce account ownership and immutable Scale v2 measurements.

Revision ID: 019
Revises: 018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "019"
down_revision = "018"

OWNED_TABLES = (
    "day_entries", "meals", "todos", "meal_templates", "training_units",
    "training_rotation", "training_sets", "exercises", "sync_log", "photos",
    "google_tokens", "exercise_progress", "dishes", "goals",
)


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("google_subject", sa.Text(), nullable=False, unique=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(f"fk_{table}_account", table, "accounts", ["account_id"], ["id"])
        op.create_index(f"ix_{table}_account_id", table, ["account_id"])
    op.create_table(
        "account_weight_ranges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False, unique=True),
        sa.Column("baseline_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("lower_offset_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("upper_offset_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("baseline_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "registered_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.Text(), nullable=False, unique=True),
        sa.Column("credential_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "scale_measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("device_id", sa.Text(), nullable=False),
        sa.Column("device_event_id", sa.Text(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("impedance_ohm", sa.Integer()),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("assignment_method", sa.Text(), nullable=False),
        sa.Column("assignment_confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("assignment_reason", sa.Text()),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("device_id", "device_event_id", name="uq_scale_measurements_device_event"),
    )


def downgrade() -> None:
    op.drop_table("scale_measurements")
    op.drop_table("registered_devices")
    op.drop_table("account_weight_ranges")
    for table in reversed(OWNED_TABLES):
        op.drop_index(f"ix_{table}_account_id", table_name=table)
        op.drop_constraint(f"fk_{table}_account", table, type_="foreignkey")
        op.drop_column(table, "account_id")
    op.drop_table("accounts")
