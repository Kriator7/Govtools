"""Create realtor_packets for Damian document-packet intake.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "realtor_packets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realtor_id", sa.Uuid(), nullable=True),
        sa.Column("packet_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message_id", sa.String(length=500), nullable=False),
        sa.Column("account", sa.String(length=200), nullable=True),
        sa.Column("from_header", sa.String(length=500), nullable=True),
        sa.Column("to_header", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("missing_fields", sa.JSON(), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("apply_result", sa.JSON(), nullable=True),
        sa.Column("raw_path", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["realtor_id"], ["realtors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "packet_number", name="uq_realtor_packet_message_number"),
    )
    op.create_index("ix_realtor_packets_public_id", "realtor_packets", ["public_id"], unique=True)
    op.create_index("ix_realtor_packets_realtor_id", "realtor_packets", ["realtor_id"])
    op.create_index("ix_realtor_packets_message_id", "realtor_packets", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_realtor_packets_message_id", table_name="realtor_packets")
    op.drop_index("ix_realtor_packets_realtor_id", table_name="realtor_packets")
    op.drop_index("ix_realtor_packets_public_id", table_name="realtor_packets")
    op.drop_table("realtor_packets")
