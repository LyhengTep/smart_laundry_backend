"""add order delivery fee

Revision ID: e5f7a9b2c4d6
Revises: d4e6f8a1b2c3
Create Date: 2026-04-21 00:00:02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e5f7a9b2c4d6"
down_revision = "d4e6f8a1b2c3"
branch_labels = None
depends_on = None


delivery_fee_paid_by = postgresql.ENUM(
    "CUSTOMER",
    "SHOP",
    name="delivery_fee_paid_by",
    create_type=False,
)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    delivery_fee_paid_by.create(bind, checkfirst=True)

    if not _has_column("orders", "delivery_fee"):
        op.add_column(
            "orders",
            sa.Column("delivery_fee", sa.Float(), nullable=False, server_default="0"),
        )
        op.alter_column("orders", "delivery_fee", server_default=None)

    if not _has_column("orders", "delivery_fee_paid_by"):
        op.add_column(
            "orders",
            sa.Column(
                "delivery_fee_paid_by",
                delivery_fee_paid_by,
                nullable=False,
                server_default="CUSTOMER",
            ),
        )
        op.alter_column("orders", "delivery_fee_paid_by", server_default=None)


def downgrade() -> None:
    if _has_column("orders", "delivery_fee_paid_by"):
        op.drop_column("orders", "delivery_fee_paid_by")
    if _has_column("orders", "delivery_fee"):
        op.drop_column("orders", "delivery_fee")

    bind = op.get_bind()
    delivery_fee_paid_by.drop(bind, checkfirst=True)
