"""add driver timestamps

Revision ID: 7c2e1f9a6d4b
Revises: 1a2b3c4d5e6f
Create Date: 2026-03-27 00:30:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c2e1f9a6d4b"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "drivers",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column(
        "drivers",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.alter_column("drivers", "created_at", server_default=None)
    op.alter_column("drivers", "updated_at", server_default=None)


def downgrade() -> None:
    op.drop_column("drivers", "updated_at")
    op.drop_column("drivers", "created_at")
