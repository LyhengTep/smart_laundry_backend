"""add payments module

Revision ID: d4e6f8a1b2c3
Revises: c6e8a1b4d2f7
Create Date: 2026-04-21 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4e6f8a1b2c3"
down_revision = "c6e8a1b4d2f7"
branch_labels = None
depends_on = None


payment_method = postgresql.ENUM(
    "CASH",
    "CARD",
    "BANK_TRANSFER",
    "E_WALLET",
    name="payment_method",
    create_type=False,
)

payment_status = postgresql.ENUM(
    "PENDING",
    "SUCCESS",
    "FAILED",
    "REFUNDED",
    name="payment_status",
    create_type=False,
)

currency_type = postgresql.ENUM(
    "KHR",
    "USD",
    name="currency_type",
    create_type=False,
)

paid_by_type = postgresql.ENUM(
    "SHOP",
    "CUSTOMER",
    name="paid_by_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    payment_method.create(bind, checkfirst=True)
    payment_status.create(bind, checkfirst=True)
    currency_type.create(bind, checkfirst=True)
    paid_by_type.create(bind, checkfirst=True)

    if not inspector.has_table("payments"):
        op.create_table(
            "payments",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("method", payment_method, nullable=False),
            sa.Column("status", payment_status, nullable=False),
            sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("currency", currency_type, nullable=False),
            sa.Column("provider_ref", sa.String(length=255), nullable=True),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("paid_by", paid_by_type, nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments (order_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_payments_order_id")
    op.execute("DROP TABLE IF EXISTS payments")

    bind = op.get_bind()
    paid_by_type.drop(bind, checkfirst=True)
    currency_type.drop(bind, checkfirst=True)
    payment_status.drop(bind, checkfirst=True)
    payment_method.drop(bind, checkfirst=True)
