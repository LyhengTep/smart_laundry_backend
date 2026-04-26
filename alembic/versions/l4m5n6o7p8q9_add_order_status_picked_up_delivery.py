"""add order status PICKED_UP_DELIVERY

Revision ID: l4m5n6o7p8q9
Revises: k3l4m5n6o7p8
Create Date: 2026-04-26

"""
from alembic import op

revision = 'l4m5n6o7p8q9'
down_revision = 'k3l4m5n6o7p8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'PICKED_UP_DELIVERY'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op
    pass
