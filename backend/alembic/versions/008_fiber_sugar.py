"""Add fiber_g and sugar_g to dishes and meals.

Revision ID: 008
Revises: 007
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"


def upgrade() -> None:
    op.add_column("dishes", sa.Column("fiber_g", sa.Numeric(6, 2), nullable=True))
    op.add_column("dishes", sa.Column("sugar_g", sa.Numeric(6, 2), nullable=True))
    op.add_column("meals", sa.Column("fiber_g", sa.Numeric(6, 2), nullable=True))
    op.add_column("meals", sa.Column("sugar_g", sa.Numeric(6, 2), nullable=True))
    op.add_column("meal_templates", sa.Column("fiber_g", sa.Numeric(6, 2), nullable=True))
    op.add_column("meal_templates", sa.Column("sugar_g", sa.Numeric(6, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("meals", "sugar_g")
    op.drop_column("meals", "fiber_g")
    op.drop_column("dishes", "sugar_g")
    op.drop_column("dishes", "fiber_g")