"""Add account body profiles and immutable BMI inputs.

Revision ID: 020
Revises: 019
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "019"


def upgrade() -> None:
    op.create_table(
        "body_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("height_cm", sa.Numeric(5, 1)),
        sa.Column("birth_date", sa.Date()),
        sa.Column("calculation_sex", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("account_id", name="uq_body_profiles_account"),
    )
    op.add_column("scale_measurements", sa.Column("bmi", sa.Numeric(4, 1)))
    op.add_column("scale_measurements", sa.Column("profile_snapshot", postgresql.JSONB()))


def downgrade() -> None:
    op.drop_column("scale_measurements", "profile_snapshot")
    op.drop_column("scale_measurements", "bmi")
    op.drop_table("body_profiles")
