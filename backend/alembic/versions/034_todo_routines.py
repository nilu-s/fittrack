"""Add account-private recurring todo routines.

Revision ID: 034
Revises: 033
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "034"
down_revision = "033"


def upgrade() -> None:
    op.create_table(
        "todo_routines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("weekdays", postgresql.JSONB(), nullable=False),
        sa.Column("due_time", sa.Time()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_todo_routines_account_id", "todo_routines", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_todo_routines_account_id", table_name="todo_routines")
    op.drop_table("todo_routines")
