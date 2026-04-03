"""make driver assignment driver_id nullable

Revision ID: a7c5e2d1f9b4
Revises: f2a4c6d8e9b1
Create Date: 2026-04-04 00:00:01
"""
from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a7c5e2d1f9b4"
down_revision = "f2a4c6d8e9b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "driver_assignments",
        "driver_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "driver_assignments",
        "driver_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
