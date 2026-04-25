"""fix payment_type enum labels to uppercase

Revision ID: h9i2j3k4l5m6
Revises: g8h1i2j3k4l5
Create Date: 2026-04-23

"""
from alembic import op

revision = 'h9i2j3k4l5m6'
down_revision = 'g8h1i2j3k4l5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE payments ALTER COLUMN type TYPE VARCHAR(50)")
    op.execute("UPDATE payments SET type = upper(type) WHERE type IS NOT NULL")
    op.execute("DROP TYPE IF EXISTS payment_type")
    op.execute(
        "CREATE TYPE payment_type AS ENUM "
        "('PICKUP_FEE', 'DELIVERY_FEE', 'WASHING_SERVICE_FEE', 'ADVANCE_SETTLEMENT')"
    )
    op.execute(
        "ALTER TABLE payments ALTER COLUMN type TYPE payment_type USING type::payment_type"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE payments ALTER COLUMN type TYPE VARCHAR(50)")
    op.execute("UPDATE payments SET type = lower(type) WHERE type IS NOT NULL")
    op.execute("DROP TYPE IF EXISTS payment_type")
    op.execute(
        "CREATE TYPE payment_type AS ENUM "
        "('pickup_fee', 'delivery_fee', 'washing_service_fee', 'advance_settlement')"
    )
    op.execute(
        "ALTER TABLE payments ALTER COLUMN type TYPE payment_type USING type::payment_type"
    )
