"""Add structured top-set and back-off configuration.

Revision ID: 018
Revises: 017
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"


def upgrade() -> None:
    op.add_column("exercises", sa.Column("top_set_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("exercises", sa.Column("backoff_set_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("exercises", sa.Column("backoff_reps_low", sa.Integer(), nullable=True))
    op.add_column("exercises", sa.Column("backoff_reps_high", sa.Integer(), nullable=True))
    op.add_column("exercises", sa.Column("backoff_weight_percent", sa.Numeric(5, 2), nullable=True))
    op.execute("""
        UPDATE exercises
        SET top_set_count = 1,
            backoff_set_count = GREATEST(target_sets::integer - 1, 0),
            backoff_reps_low = base_reps_low,
            backoff_reps_high = base_reps_high,
            backoff_weight_percent = 90
        WHERE is_topset = true
    """)


def downgrade() -> None:
    op.drop_column("exercises", "backoff_weight_percent")
    op.drop_column("exercises", "backoff_reps_high")
    op.drop_column("exercises", "backoff_reps_low")
    op.drop_column("exercises", "backoff_set_count")
    op.drop_column("exercises", "top_set_count")
