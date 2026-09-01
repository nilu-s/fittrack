"""Add complete nutrient fields to account-owned foods.

Revision ID: 036
Revises: 035
"""
from alembic import op
import sqlalchemy as sa


revision = "036"
down_revision = "035"


_COLUMNS = (
    "saturated_fat_g", "sodium_mg", "potassium_mg", "calcium_mg", "magnesium_mg",
    "iron_mg", "zinc_mg", "vitamin_a_ug", "vitamin_c_mg", "vitamin_d_ug",
    "vitamin_b12_ug", "folate_ug",
)


def upgrade() -> None:
    # Existing foods and immutable historical snapshots stay truthful: no
    # micronutrient is invented during the additive migration.
    for name in _COLUMNS:
        op.add_column("foods", sa.Column(f"{name}_per_100g", sa.Numeric(10, 4), nullable=True))


def downgrade() -> None:
    for name in reversed(_COLUMNS):
        op.drop_column("foods", f"{name}_per_100g")
