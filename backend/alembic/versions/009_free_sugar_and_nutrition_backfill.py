"""Track free sugars and backfill nutrition estimates for default dishes.

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"

NUTRITION_ESTIMATES = {
    "Cheesecake-Bowl": (9, 24, 8),
    "Pasta Pomodore": (8, 10, 4),
    "Teriyaki-Tofu-Bowl": (11, 17, 10),
    "Banana-Whey-Cream": (4, 20, 0),
    "Smoky Loaded Potatoes": (12, 12, 5),
    "More Fizz Ballaststoff-Limo Mojito": (5, 0, 0),
}


def upgrade() -> None:
    for table in ("dishes", "meals", "meal_templates"):
        op.add_column(table, sa.Column("free_sugar_g", sa.Numeric(6, 2), nullable=True))
        for name, (fiber, total_sugar, free_sugar) in NUTRITION_ESTIMATES.items():
            op.execute(
                sa.text(
                    f"UPDATE {table} "
                    "SET fiber_g = :fiber, sugar_g = :total_sugar, free_sugar_g = :free_sugar "
                    "WHERE name = :name"
                ).bindparams(
                    fiber=fiber,
                    total_sugar=total_sugar,
                    free_sugar=free_sugar,
                    name=name,
                )
            )


def downgrade() -> None:
    for table in ("meal_templates", "meals", "dishes"):
        op.drop_column(table, "free_sugar_g")
