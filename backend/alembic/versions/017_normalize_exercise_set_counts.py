"""Store gym set targets as plain numeric counts.

Revision ID: 017
Revises: 016
"""
from alembic import op

revision = "017"
down_revision = "016"


def upgrade() -> None:
    op.execute("""
        UPDATE exercises AS exercise
        SET target_sets = normalized.set_count::text
        FROM (
            SELECT id, SUM((match.parts)[1]::integer) AS set_count
            FROM exercises
            CROSS JOIN LATERAL regexp_matches(target_sets, '([0-9]+)[[:space:]]*[×x]', 'g') AS match(parts)
            GROUP BY id
        ) AS normalized
        WHERE exercise.id = normalized.id
    """)


def downgrade() -> None:
    pass
