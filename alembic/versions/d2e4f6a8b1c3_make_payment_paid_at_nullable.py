"""make payment paid_at nullable

Revision ID: d2e4f6a8b1c3
Revises: c1d3e5f7a9b2
Create Date: 2026-04-23

"""
from alembic import op

revision = 'd2e4f6a8b1c3'
down_revision = 'c1d3e5f7a9b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('payments', 'paid_at', nullable=True)


def downgrade() -> None:
    op.alter_column('payments', 'paid_at', nullable=False)
