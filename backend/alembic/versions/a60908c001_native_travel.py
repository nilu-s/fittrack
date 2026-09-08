"""Revocable native sessions and private travel monitoring.

Revision ID: a60908c001
Revises: f5a6b7c8d901
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "a60908c001"
down_revision = "f5a6b7c8d901"
branch_labels = None
depends_on = None


def identity():
    return sa.Column("id", sa.UUID(), primary_key=True)


def owner(nullable=False):
    return sa.Column("account_id", sa.UUID(), sa.ForeignKey("accounts.id"), nullable=nullable)


def upgrade():
    op.create_table("native_logins", identity(),
        sa.Column("account_id", sa.UUID(), sa.ForeignKey("accounts.id", ondelete="CASCADE")),
        sa.Column("challenge", sa.Text(), nullable=False), sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("native_sessions", identity(), owner(),
        sa.Column("credential_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("platform", sa.Text(), nullable=False), sa.Column("push_token", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_native_sessions_account_id", "native_sessions", ["account_id"])
    op.create_table("travel_watches", identity(), owner(),
        sa.Column("todo_id", sa.UUID(), sa.ForeignKey("todos.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("device_id", sa.UUID(), sa.ForeignKey("native_sessions.id", ondelete="SET NULL")),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("plan_hash", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="Europe/Berlin"),
        sa.Column("lead_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("origin", JSONB()), sa.Column("live_fix", JSONB()),
        sa.Column("live_until", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("depart_at", sa.DateTime(timezone=True)), sa.Column("arrival_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer()), sa.Column("error", sa.Text()),
        sa.Column("notified_depart_at", sa.DateTime(timezone=True)), sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("departure_change_minutes", sa.Integer()), sa.Column("departure_changed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_travel_watches_account_id", "travel_watches", ["account_id"])
    op.create_index("ix_travel_watches_next_check_at", "travel_watches", ["next_check_at"])
    op.create_table("travel_notifications", identity(), owner(),
        sa.Column("watch_id", sa.UUID(), sa.ForeignKey("travel_watches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False), sa.Column("event_key", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("discarded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("watch_id", "generation", "event_key", name="uq_travel_notification_event"))
    op.create_index("ix_travel_notifications_account_id", "travel_notifications", ["account_id"])


def downgrade():
    for table in ("travel_notifications", "travel_watches", "native_sessions", "native_logins"):
        op.drop_table(table)
