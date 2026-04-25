"""add order has_advance_settlement

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'j2k3l4m5n6o7'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('has_advance_settlement', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('orders', 'has_advance_settlement')
