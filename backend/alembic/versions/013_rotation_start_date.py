"""Add start dates to rotation entries.

Revision ID: 013
Revises: 012
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"


def upgrade() -> None:
    op.add_column("training_rotation", sa.Column("start_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("training_rotation", "start_date")
