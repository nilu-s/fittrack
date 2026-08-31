"""Add confirmed photo-analysis provenance for configurable meal entries.

Revision ID: 023
Revises: 022
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023"
down_revision = "022"


def upgrade() -> None:
    op.add_column("photos", sa.Column("meal_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meal_entries.id", ondelete="SET NULL")))
    op.create_index("ix_photos_account_meal_entry", "photos", ["account_id", "meal_entry_id"])
    op.create_table(
        "meal_photo_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("meal_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meal_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("analysis", postgresql.JSONB()), sa.Column("provider", sa.Text()), sa.Column("model", sa.Text()), sa.Column("schema_version", sa.Text()), sa.Column("error_code", sa.Text()),
        sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("state IN ('pending', 'accepted', 'rejected', 'failed')", name="ck_meal_photo_analysis_state"),
    )
    op.create_index("ix_meal_photo_analyses_account_entry", "meal_photo_analyses", ["account_id", "meal_entry_id"])


def downgrade() -> None:
    op.drop_table("meal_photo_analyses")
    op.drop_index("ix_photos_account_meal_entry", table_name="photos")
    op.drop_column("photos", "meal_entry_id")
