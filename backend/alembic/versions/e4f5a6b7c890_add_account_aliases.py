"""Add permanent public account aliases.

Revision ID: e4f5a6b7c890
Revises: d3e4f5a6b789, f0f8c1a92cde
"""
from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c890"
down_revision = ("d3e4f5a6b789", "f0f8c1a92cde")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing accounts choose a handle at their next authenticated visit.
    # New accounts complete that same short onboarding flow after Google OAuth.
    op.add_column("accounts", sa.Column("alias", sa.Text(), nullable=True))
    op.create_index("ix_accounts_alias", "accounts", ["alias"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_accounts_alias", table_name="accounts")
    op.drop_column("accounts", "alias")
