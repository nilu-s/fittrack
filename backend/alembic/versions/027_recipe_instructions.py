"""Add structured cooking directions to account-owned recipes.

Revision ID: 027
Revises: 026
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "027"
down_revision = "026"


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column(
            "instructions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("recipes", "instructions")
