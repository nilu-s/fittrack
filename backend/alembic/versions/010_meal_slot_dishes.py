"""Add slot-specific high-protein meal alternatives.

Revision ID: 010
Revises: 009
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"

DISHES = [
    # slot, name, kcal, protein, carbs, fat, fiber, sugar, free_sugar
    (1, "Protein-Porridge Apfel-Zimt", 560, 45, 64, 12, 11, 18, 0),
    (1, "Skyr-Beeren-Crunch", 520, 48, 52, 13, 12, 17, 1),
    (2, "Chicken-Rice-Bowl", 780, 58, 82, 18, 9, 8, 1),
    (2, "Pasta Pomodore", 740, 47, 91, 18, 8, 10, 4),
    (3, "Skyr-Beeren-Crunch Snack", 300, 31, 31, 7, 7, 16, 0),
    (3, "Protein-Pudding Banane", 290, 33, 29, 6, 5, 18, 0),
    (4, "Turkey-Chili-Bowl", 790, 60, 66, 24, 15, 12, 2),
    (4, "Salmon-Potato-Bowl", 810, 55, 58, 31, 9, 7, 0),
]


def upgrade() -> None:
    for slot, name, kcal, protein, carbs, fat, fiber, sugar, free_sugar in DISHES:
        op.execute(
            sa.text(
                "INSERT INTO dishes (id, user_id, slot, name, kcal, protein_g, carbs_g, "
                "fat_g, fiber_g, sugar_g, free_sugar_g, is_default, usage_count, source) "
                "VALUES (gen_random_uuid(), :user_id, :slot, :name, :kcal, :protein, "
                ":carbs, :fat, :fiber, :sugar, :free_sugar, false, 0, 'seed') "
                "ON CONFLICT (user_id, name) DO NOTHING"
            ).bindparams(
                user_id="luis",
                slot=slot,
                name=name,
                kcal=kcal,
                protein=protein,
                carbs=carbs,
                fat=fat,
                fiber=fiber,
                sugar=sugar,
                free_sugar=free_sugar,
            )
        )


def downgrade() -> None:
    names = ", ".join("'" + name.replace("'", "''") + "'" for _, name, *_ in DISHES)
    op.execute(sa.text(f"DELETE FROM dishes WHERE user_id = 'luis' AND name IN ({names}) AND source = 'seed'"))
