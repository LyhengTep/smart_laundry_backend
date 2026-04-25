"""add payment settled_by_payment_id

Revision ID: i1j2k3l4m5n6
Revises: h9i2j3k4l5m6
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'i1j2k3l4m5n6'
down_revision = 'h9i2j3k4l5m6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('settled_by_payment_id', sa.UUID(), nullable=True))
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
