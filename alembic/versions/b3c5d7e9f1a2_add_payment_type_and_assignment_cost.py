"""add payment type and assignment cost

Revision ID: b3c5d7e9f1a2
Revises: a2b4c6d8e1f3
Create Date: 2026-04-22

"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c5d7e9f1a2'
down_revision = 'a2b4c6d8e1f3'
branch_labels = None
depends_on = None

payment_type_enum = sa.Enum('pickup_fee', 'final_payment', name='payment_type')


def upgrade() -> None:
    payment_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'payments',
        sa.Column('type', sa.Enum('pickup_fee', 'final_payment', name='payment_type'), nullable=True),
    )
    op.add_column(
        'driver_assignments',
        sa.Column('cost', sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('driver_assignments', 'cost')
    op.drop_column('payments', 'type')
    payment_type_enum.drop(op.get_bind(), checkfirst=True)
