"""add user msg token

Revision ID: f4d8c1a2b7e9
Revises: c2d7f7e4a901
Create Date: 2026-03-26 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4d8c1a2b7e9"
down_revision = "c2d7f7e4a901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("msg_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "msg_token")
