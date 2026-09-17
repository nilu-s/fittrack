"""Retired historical pictogram catalogue revision.

The original schema was deployed before Pictogramicl replaced Cronicl's local
catalogue.  Retain only this no-op bridge so existing databases can advance.
"""

revision = "2b3c4d5e6f78"
down_revision = "f9a0b1c2d345"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
