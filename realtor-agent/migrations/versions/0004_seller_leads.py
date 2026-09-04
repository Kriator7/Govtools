"""Create seller_leads for PirateEye public-source home hunt.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seller_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realtor_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=8), nullable=False),
        sa.Column("zip_code", sa.String(length=16), nullable=True),
        sa.Column("person_name", sa.String(length=200), nullable=True),
        sa.Column("street_address", sa.String(length=300), nullable=True),
        sa.Column("asking_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_only", sa.Boolean(), nullable=False),
        sa.Column("assessor_url", sa.String(length=500), nullable=True),
        sa.Column("listing_id", sa.Uuid(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.ForeignKeyConstraint(["realtor_id"], ["realtors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("realtor_id", "fingerprint", name="uq_seller_lead_realtor_fingerprint"),
    )
    op.create_index("ix_seller_leads_source", "seller_leads", ["source"])
    op.create_index("ix_seller_leads_status", "seller_leads", ["status"])
    op.create_index("ix_seller_leads_fingerprint", "seller_leads", ["fingerprint"])
    op.create_index("ix_seller_leads_realtor_id", "seller_leads", ["realtor_id"])


def downgrade() -> None:
    op.drop_index("ix_seller_leads_realtor_id", table_name="seller_leads")
    op.drop_index("ix_seller_leads_fingerprint", table_name="seller_leads")
    op.drop_index("ix_seller_leads_status", table_name="seller_leads")
    op.drop_index("ix_seller_leads_source", table_name="seller_leads")
    op.drop_table("seller_leads")
