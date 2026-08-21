"""Add training units and recurrence fields to the rotation plan.

Revision ID: 012
Revises: 011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"


def upgrade() -> None:
    op.create_table(
        "training_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text(), nullable=False, server_default="luis"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("user_id", "name", name="uq_training_units_user_name"),
    )
    op.add_column("training_rotation", sa.Column("frequency_weeks", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("training_rotation", sa.Column("week_offset", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("training_rotation", "week_offset")
    op.drop_column("training_rotation", "frequency_weeks")
    op.drop_table("training_units")
