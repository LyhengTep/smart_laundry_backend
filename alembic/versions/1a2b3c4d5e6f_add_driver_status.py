"""add driver status

Revision ID: 1a2b3c4d5e6f
Revises: f4d8c1a2b7e9
Create Date: 2026-03-27 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e6f"
down_revision = "f4d8c1a2b7e9"
branch_labels = None
depends_on = None


driver_status = postgresql.ENUM(
    "OFFLINE",
    "ONLINE",
    "BUSY",
    "PICKING_UP",
    "DELIVERING",
    "ON_BREAK",
    name="driver_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    driver_status.create(bind, checkfirst=True)
    op.add_column(
        "drivers",
        sa.Column(
            "driver_status",
            driver_status,
            nullable=False,
            server_default="OFFLINE",
        ),
    )
    op.alter_column("drivers", "driver_status", server_default=None)


def downgrade() -> None:
    op.drop_column("drivers", "driver_status")
    bind = op.get_bind()
    driver_status.drop(bind, checkfirst=True)
