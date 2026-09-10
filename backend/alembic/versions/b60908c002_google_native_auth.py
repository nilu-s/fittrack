"""Version native Google sessions and irreversibly revoke browser-handoff v1."""
from alembic import op
import sqlalchemy as sa

revision = "b60908c002"
down_revision = "a60908c001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("native_logins", sa.Column("protocol_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("native_logins", sa.Column("nonce_hash", sa.Text()))
    op.add_column("native_sessions", sa.Column("protocol_version", sa.Integer(), nullable=False, server_default="1"))
    op.execute("UPDATE native_logins SET consumed = true")
    op.execute("UPDATE native_sessions SET revoked = true, push_token = NULL")
    op.execute("""UPDATE travel_watches SET active = false, generation = generation + 1,
        origin = NULL, live_fix = NULL, live_until = NULL, checked_at = NULL,
        depart_at = NULL, arrival_at = NULL, duration_seconds = NULL, error = NULL
        WHERE device_id IS NOT NULL""")
    op.execute("""UPDATE travel_notifications SET discarded = true WHERE watch_id IN
        (SELECT id FROM travel_watches WHERE device_id IS NOT NULL) AND sent_at IS NULL""")


def downgrade():
    # Never restore credentials, push tokens or locations invalidated by upgrade.
    op.execute("UPDATE native_sessions SET revoked = true, push_token = NULL")
    op.execute("UPDATE native_logins SET consumed = true")
    op.drop_column("native_sessions", "protocol_version")
    op.drop_column("native_logins", "nonce_hash")
    op.drop_column("native_logins", "protocol_version")
