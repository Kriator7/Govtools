"""Add ARV screening fields for Pirates IG LLC.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("arv", sa.Numeric(12, 2), nullable=True))
    op.add_column("investor_criteria", sa.Column("max_price_pct_of_arv", sa.Numeric(6, 4), nullable=True))
    op.add_column("investor_criteria", sa.Column("preferred_financing", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("investor_criteria", "preferred_financing")
    op.drop_column("investor_criteria", "max_price_pct_of_arv")
    op.drop_column("listings", "arv")
