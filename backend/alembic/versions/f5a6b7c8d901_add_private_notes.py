"""Add private-first notes and the todo origin link.

Revision ID: f5a6b7c8d901
Revises: e4f5a6b7c890
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "f5a6b7c8d901"
down_revision = "e4f5a6b7c890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("space_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_space_id", "notes", ["space_id"])
    op.add_column("todos", sa.Column("origin_note_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_todos_origin_note_id", "todos", "notes", ["origin_note_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_todos_origin_note_id", "todos", ["origin_note_id"])


def downgrade() -> None:
    op.drop_constraint("uq_todos_origin_note_id", "todos", type_="unique")
    op.drop_constraint("fk_todos_origin_note_id", "todos", type_="foreignkey")
    op.drop_column("todos", "origin_note_id")
    op.drop_index("ix_notes_space_id", table_name="notes")
    op.drop_table("notes")
