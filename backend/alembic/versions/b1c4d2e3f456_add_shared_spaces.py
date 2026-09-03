"""Add explicit shared spaces, projects and optional shared task/list scope.

Revision ID: b1c4d2e3f456
Revises: f0f8c1a92cde
Create Date: 2026-09-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b1c4d2e3f456"
down_revision = "f0f8c1a92cde"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("owner_account_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "space_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("space_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "account_id", name="uq_space_memberships_space_account"),
    )
    op.create_table(
        "space_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("space_id", sa.UUID(), nullable=False),
        sa.Column("invited_account_id", sa.UUID(), nullable=False),
        sa.Column("invited_by_account_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["invited_by_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "space_projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("space_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_by_account_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "name", name="uq_space_projects_space_name"),
    )
    op.add_column("todos", sa.Column("space_id", sa.UUID(), nullable=True))
    op.add_column("todos", sa.Column("project_id", sa.UUID(), nullable=True))
    op.add_column("todos", sa.Column("assignee_account_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_todos_space_id", "todos", "spaces", ["space_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_todos_project_id", "todos", "space_projects", ["project_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_todos_assignee_account_id", "todos", "accounts", ["assignee_account_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_todos_space_id", "todos", ["space_id"])
    op.add_column("shopping_lists", sa.Column("space_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_shopping_lists_space_id", "shopping_lists", "spaces", ["space_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_shopping_lists_space_id", "shopping_lists", ["space_id"])


def downgrade() -> None:
    op.drop_index("ix_shopping_lists_space_id", table_name="shopping_lists")
    op.drop_constraint("fk_shopping_lists_space_id", "shopping_lists", type_="foreignkey")
    op.drop_column("shopping_lists", "space_id")
    op.drop_index("ix_todos_space_id", table_name="todos")
    op.drop_constraint("fk_todos_assignee_account_id", "todos", type_="foreignkey")
    op.drop_constraint("fk_todos_project_id", "todos", type_="foreignkey")
    op.drop_constraint("fk_todos_space_id", "todos", type_="foreignkey")
    op.drop_column("todos", "assignee_account_id")
    op.drop_column("todos", "project_id")
    op.drop_column("todos", "space_id")
    op.drop_table("space_projects")
    op.drop_table("space_invitations")
    op.drop_table("space_memberships")
    op.drop_table("spaces")
