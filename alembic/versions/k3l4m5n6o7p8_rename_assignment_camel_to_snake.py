"""rename assignedAt and deliveryAt to assigned_at and delivery_at

Revision ID: k3l4m5n6o7p8
Revises: j2k3l4m5n6o7
Create Date: 2026-04-26

"""
from alembic import op

revision = 'k3l4m5n6o7p8'
down_revision = 'j2k3l4m5n6o7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('driver_assignments', 'assignedAt', new_column_name='assigned_at')
    op.alter_column('driver_assignments', 'deliveryAt', new_column_name='delivery_at')


def downgrade() -> None:
    op.alter_column('driver_assignments', 'assigned_at', new_column_name='assignedAt')
    op.alter_column('driver_assignments', 'delivery_at', new_column_name='deliveryAt')
