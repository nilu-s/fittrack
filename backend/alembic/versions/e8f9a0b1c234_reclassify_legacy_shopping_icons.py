"""Reclassify generic legacy shopping tiles with article-level symbols.

Revision ID: e8f9a0b1c234
Revises: d7e8f9a0b123
Create Date: 2026-09-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.services.shopping_icons import LEGACY_GENERIC_ICON_KEYS, classify_article, normalize_article_title


revision = "e8f9a0b1c234"
down_revision = "d7e8f9a0b123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade old category/bag tiles without replacing an explicit choice.

    Product titles remain local to ``shopping_items``.  This migration neither
    logs them nor adds them to the shared catalogue.
    """
    connection = op.get_bind()
    rows = connection.execute(sa.text("""
        SELECT id, account_id, title
        FROM shopping_items
        WHERE icon_key IN :legacy_keys
    """).bindparams(sa.bindparam("legacy_keys", expanding=True)), {"legacy_keys": list(LEGACY_GENERIC_ICON_KEYS)})

    for row in rows:
        has_explicit_choice = connection.execute(sa.text("""
            SELECT 1
            FROM shopping_icon_preferences
            WHERE account_id = :account_id AND normalized_title = :normalized_title
            LIMIT 1
        """), {"account_id": row.account_id, "normalized_title": normalize_article_title(row.title)}).scalar()
        if has_explicit_choice:
            continue
        category_key, icon_key = classify_article(row.title)
        if icon_key == "initials":
            continue
        connection.execute(sa.text("""
            UPDATE shopping_items
            SET category_key = :category_key, icon_key = :icon_key
            WHERE id = :item_id
        """), {"category_key": category_key, "icon_key": icon_key, "item_id": row.id})


def downgrade() -> None:
    # The prior generic icon cannot be reconstructed after an improved match.
    # This intentionally leaves the better, article-specific presentation.
    pass
