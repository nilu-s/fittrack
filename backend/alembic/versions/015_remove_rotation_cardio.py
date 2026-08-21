"""Remove legacy cardio settings from rotation entries.

Revision ID: 015
Revises: 014
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"


def upgrade() -> None:
    op.drop_column("training_rotation", "cardio_minutes")


def downgrade() -> None:
    op.add_column("training_rotation", sa.Column("cardio_minutes", sa.Integer(), nullable=True))
