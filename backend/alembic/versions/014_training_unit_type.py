"""Add explicit type and cardio target to training units.

Revision ID: 014
Revises: 013
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"


def upgrade() -> None:
    op.add_column("training_units", sa.Column("unit_type", sa.Text(), nullable=False, server_default="gym"))
    op.add_column("training_units", sa.Column("cardio_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("training_units", "cardio_minutes")
    op.drop_column("training_units", "unit_type")
