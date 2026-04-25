"""fix payment_type enum labels to lowercase

Revision ID: g8h1i2j3k4l5
Revises: f7b9c1d3e5a4
Create Date: 2026-04-23

"""
from alembic import op

revision = 'g8h1i2j3k4l5'
down_revision = 'f7b9c1d3e5a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cast column to text, recreate enum with lowercase labels, recast
    op.execute("ALTER TABLE payments ALTER COLUMN type TYPE VARCHAR(50)")
    # Normalize any uppercase stored values to lowercase
    op.execute("UPDATE payments SET type = lower(type) WHERE type IS NOT NULL")
    op.execute("DROP TYPE IF EXISTS payment_type")
    op.execute(
        "CREATE TYPE payment_type AS ENUM "
        "('pickup_fee', 'delivery_fee', 'washing_service_fee', 'advance_settlement')"
    )
    op.execute(
        "ALTER TABLE payments ALTER COLUMN type TYPE payment_type USING type::payment_type"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE payments ALTER COLUMN type TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS payment_type")
    op.execute(
        "CREATE TYPE payment_type AS ENUM "
        "('PICKUP_FEE', 'DELIVERY_FEE', 'WASHING_SERVICE_FEE', 'ADVANCE_SETTLEMENT')"
    )
    op.execute(
        "ALTER TABLE payments ALTER COLUMN type TYPE payment_type USING type::payment_type"
    )
