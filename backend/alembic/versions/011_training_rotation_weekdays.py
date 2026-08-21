"""Add optional weekdays to the sport-program rotation.

Revision ID: 011
Revises: 010
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"


def upgrade() -> None:
    op.add_column("training_rotation", sa.Column("weekday", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("training_rotation", "weekday")
