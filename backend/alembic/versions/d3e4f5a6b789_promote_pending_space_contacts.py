"""Promote legacy pending space invitations to direct memberships.

Revision ID: d3e4f5a6b789
Revises: c2d3e4f5a678
"""
from alembic import op

revision = "d3e4f5a6b789"
down_revision = "c2d3e4f5a678"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO space_memberships (id, space_id, account_id, role, created_at)
        SELECT md5(random()::text || clock_timestamp()::text)::uuid, invitation.space_id, invitation.invited_account_id, 'member', now()
        FROM space_invitations invitation
        WHERE invitation.status = 'pending'
          AND NOT EXISTS (
            SELECT 1 FROM space_memberships membership
            WHERE membership.space_id = invitation.space_id
              AND membership.account_id = invitation.invited_account_id
          )
    """)
    op.execute("UPDATE space_invitations SET status = 'accepted', responded_at = now() WHERE status = 'pending'")


def downgrade() -> None:
    # Data promotion is intentionally irreversible: the product no longer has
    # a pending invitation state for confirmed contacts.
    pass
