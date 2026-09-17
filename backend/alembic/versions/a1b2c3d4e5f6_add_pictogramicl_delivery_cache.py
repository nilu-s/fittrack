"""Cache opaque Pictogramicl delivery results.

Revision ID: a1b2c3d4e5f6
Revises: f9a0b1c2d345
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "2b3c4d5e6f78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("pictogram_delivery_cache", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("cache_key", sa.Text(), nullable=False), sa.Column("state", sa.Text(), nullable=False), sa.Column("concept_key", sa.Text()), sa.Column("revision", sa.Integer()), sa.Column("placeholder_initial", sa.Text()), sa.Column("placeholder_revision", sa.Integer()), sa.Column("etag", sa.Text()), sa.Column("svg_markup", sa.Text(), nullable=False), sa.Column("retry_after", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("cache_key", name="uq_pictogram_delivery_cache_key"))


def downgrade() -> None:
    op.drop_table("pictogram_delivery_cache")
