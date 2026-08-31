"""Retain immutable plan revisions and never delete referenced plan items.

Revision ID: 025
Revises: 024
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "025"
down_revision = "024"


def upgrade() -> None:
    op.add_column("meal_plan_items", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("meal_entries", sa.Column("meal_plan_version", sa.Integer()))
    op.create_table(
        "meal_plan_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("meal_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("items_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("meal_plan_id", "version", name="uq_meal_plan_versions_plan_version"),
    )
    op.create_index("ix_meal_plan_versions_account_plan", "meal_plan_versions", ["account_id", "meal_plan_id"])
    op.execute("UPDATE meal_entries SET meal_plan_version = 1 WHERE meal_plan_id IS NOT NULL")
    # Backfill a first audit snapshot for every plan that pre-dates this
    # migration. JSON construction intentionally stores IDs as strings.
    op.execute("""
        INSERT INTO meal_plan_versions (id, account_id, meal_plan_id, version, name, items_snapshot)
        SELECT gen_random_uuid(), p.account_id, p.id, p.version, p.name,
               COALESCE(jsonb_agg(jsonb_build_object(
                 'category_id', i.category_id::text,
                 'recipe_id', i.recipe_id::text,
                 'name', i.name,
                 'planned_time', i.planned_time::text,
                 'weekdays', i.weekdays,
                 'portion', i.portion::text,
                 'sort_order', i.sort_order
               ) ORDER BY i.sort_order) FILTER (WHERE i.id IS NOT NULL), '[]'::jsonb)
        FROM meal_plans p
        LEFT JOIN meal_plan_items i ON i.meal_plan_id = p.id AND i.account_id = p.account_id
        GROUP BY p.id, p.account_id, p.version, p.name
    """)


def downgrade() -> None:
    op.drop_index("ix_meal_plan_versions_account_plan", table_name="meal_plan_versions")
    op.drop_table("meal_plan_versions")
    op.drop_column("meal_entries", "meal_plan_version")
    op.drop_column("meal_plan_items", "is_active")
