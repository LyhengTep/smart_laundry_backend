"""update order status enum

Revision ID: 8f3c1d2a4b5c
Revises: a1f4e276f031
Create Date: 2026-03-18 00:00:01
"""
from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "8f3c1d2a4b5c"
down_revision = "a1f4e276f031"
branch_labels = None
depends_on = None


old_order_status = postgresql.ENUM(
    "PENDING",
    "ACCEPTED",
    "PICKED_UP",
    "DELIVERED_TO_SHOP",
    "WASHING",
    "READY_FOR_DELIVERY",
    "OUT_FOR_DELIVERY",
    "COMPLETED",
    "CANCELLED",
    name="order_status",
)

new_order_status = postgresql.ENUM(
    "PENDING",
    "CONFIRMED",
    "PICKUP_ASSIGNED",
    "OUT_FOR_PICKUP",
    "PICKED_UP",
    "DELIVERED_TO_SHOP",
    "PROCESSING",
    "READY_FOR_DELIVERY",
    "DELIVERY_ASSIGNED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "CANCELLED",
    name="order_status_new",
)


def upgrade() -> None:
    bind = op.get_bind()

    new_order_status.create(bind, checkfirst=True)
    op.execute(
        """
        ALTER TABLE orders
        ALTER COLUMN status TYPE order_status_new
        USING (
            CASE status::text
                WHEN 'ACCEPTED' THEN 'CONFIRMED'
                WHEN 'WASHING' THEN 'PROCESSING'
                WHEN 'COMPLETED' THEN 'DELIVERED'
                ELSE status::text
            END
        )::order_status_new
        """
    )
    op.execute("DROP TYPE order_status")
    op.execute("ALTER TYPE order_status_new RENAME TO order_status")


def downgrade() -> None:
    bind = op.get_bind()

    old_order_status.create(bind, checkfirst=True)
    op.execute(
        """
        ALTER TABLE orders
        ALTER COLUMN status TYPE order_status
        USING (
            CASE status::text
                WHEN 'CONFIRMED' THEN 'ACCEPTED'
                WHEN 'PICKUP_ASSIGNED' THEN 'ACCEPTED'
                WHEN 'OUT_FOR_PICKUP' THEN 'ACCEPTED'
                WHEN 'PROCESSING' THEN 'WASHING'
                WHEN 'DELIVERY_ASSIGNED' THEN 'READY_FOR_DELIVERY'
                WHEN 'DELIVERED' THEN 'COMPLETED'
                ELSE status::text
            END
        )::order_status
        """
    )
    op.execute("DROP TYPE order_status_new")
