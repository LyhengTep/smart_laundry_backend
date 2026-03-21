"""init

Revision ID: b9a91db121fe
Revises: 
Create Date: 2026-03-14 02:23:22.712005
"""
from __future__ import annotations

from alembic import op
import logging
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql




# revision identifiers, used by Alembic.
revision = 'b9a91db121fe'
down_revision = None
branch_labels = None
depends_on = None






order_status = postgresql.ENUM(
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
    create_type=False,
)

pickup_method = postgresql.ENUM(
    "PICKUP",
    "DROP_OFF",
    name="pickup_method",
    create_type=False,
)

order_item_price_type = postgresql.ENUM(
    "PER_ITEM",
    "PER_WEIGHT",
    "FIXED",
    name="order_item_price_type",
    create_type=False,
)

def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    order_status.create(bind, checkfirst=True)
    pickup_method.create(bind, checkfirst=True)
    order_item_price_type.create(bind, checkfirst=True)
    logging.info("Starting upgrade: creating orders and order_items tables")
    if not inspector.has_table("orders"):
        op.create_table(
            "orders",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_no", sa.String(length=32), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", order_status, nullable=False),
            sa.Column("pickup_method", pickup_method, nullable=False),
            sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("scheduled_pickup_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("scheduled_dropoff_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pickup_address", sa.String(length=255), nullable=False),
            sa.Column("delivery_address", sa.String(length=255), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("subtotal", sa.Float(), nullable=False),
            sa.Column("discount", sa.Float(), nullable=False),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["business_id"], ["laundry_businesses.id"]),
            sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_id ON orders (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON orders (customer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_business_id ON orders (business_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_driver_id ON orders (driver_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_order_no ON orders (order_no)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status)")

    if not inspector.has_table("order_items"):
        op.create_table(
            "order_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("business_service_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("service_id", sa.Integer(), nullable=False),
            sa.Column("service_name", sa.String(length=100), nullable=False),
            sa.Column("pricing_type", order_item_price_type, nullable=False),
            sa.Column("measure_type", sa.String(length=30), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("sub_total", sa.Float(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["business_service_id"], ["business_services.id"]),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["service_id"], ["laundry_services.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_order_items_id ON order_items (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items (order_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_order_items_business_service_id ON order_items (business_service_id)"
    )



def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
