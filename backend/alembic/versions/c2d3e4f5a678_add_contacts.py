"""Add private contacts and consent-based invitations.

Revision ID: c2d3e4f5a678
Revises: b1c4d2e3f456
"""
from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a678"
down_revision = "b1c4d2e3f456"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("contacts", sa.Column("id", sa.UUID(), nullable=False), sa.Column("owner_account_id", sa.UUID(), nullable=False), sa.Column("contact_account_id", sa.UUID(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["owner_account_id"], ["accounts.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["contact_account_id"], ["accounts.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("owner_account_id", "contact_account_id", name="uq_contacts_owner_contact"))
    op.create_table("contact_invitations", sa.Column("id", sa.UUID(), nullable=False), sa.Column("invited_account_id", sa.UUID(), nullable=False), sa.Column("invited_by_account_id", sa.UUID(), nullable=False), sa.Column("status", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("responded_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["invited_account_id"], ["accounts.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["invited_by_account_id"], ["accounts.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))

def downgrade() -> None:
    op.drop_table("contact_invitations"); op.drop_table("contacts")
