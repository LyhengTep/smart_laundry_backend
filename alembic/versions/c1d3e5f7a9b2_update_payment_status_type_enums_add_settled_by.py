"""update payment status/type enums and add settled_by_payment_id

Revision ID: c1d3e5f7a9b2
Revises: b3c5d7e9f1a2
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d3e5f7a9b2'
down_revision = 'b3c5d7e9f1a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- payment_status: drop old, create new ---
    op.execute("ALTER TABLE payments ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("UPDATE payments SET status = 'COLLECTED' WHERE status = 'SUCCESS'")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute(
        "CREATE TYPE payment_status AS ENUM "
        "('PENDING', 'COLLECTED', 'FAILED', 'REFUNDED', 'PENDING_SETTLEMENT', 'SETTLED')"
    )
    op.execute("ALTER TABLE payments ALTER COLUMN status TYPE payment_status USING status::payment_status")

    # --- payment_type: drop old, create new ---
    op.execute("ALTER TABLE payments ALTER COLUMN type TYPE VARCHAR(50)")
    op.execute("UPDATE payments SET type = 'delivery_fee' WHERE type = 'final_payment'")
    op.execute("DROP TYPE IF EXISTS payment_type")
    op.execute(
        "CREATE TYPE payment_type AS ENUM "
        "('pickup_fee', 'delivery_fee', 'washing_service_fee', 'advance_settlement')"
    )
    op.execute(
        "ALTER TABLE payments ALTER COLUMN type TYPE payment_type USING type::payment_type"
    )

    # --- settled_by_payment_id ---
    op.add_column(
        'payments',
        sa.Column('settled_by_payment_id', sa.UUID(), nullable=True),
    )
    op.create_index('ix_payments_settled_by_payment_id', 'payments', ['settled_by_payment_id'])
    op.create_foreign_key(
        'fk_payments_settled_by_payment_id',
        'payments', 'payments',
        ['settled_by_payment_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_payments_settled_by_payment_id', 'payments', type_='foreignkey')
    op.drop_index('ix_payments_settled_by_payment_id', table_name='payments')
    op.drop_column('payments', 'settled_by_payment_id')

    op.execute("ALTER TABLE payments ALTER COLUMN type TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS payment_type")
    op.execute("CREATE TYPE payment_type AS ENUM ('pickup_fee', 'final_payment')")
    op.execute("ALTER TABLE payments ALTER COLUMN type TYPE payment_type USING type::payment_type")

    op.execute("ALTER TABLE payments ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("CREATE TYPE payment_status AS ENUM ('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED')")
    op.execute("ALTER TABLE payments ALTER COLUMN status TYPE payment_status USING status::payment_status")
