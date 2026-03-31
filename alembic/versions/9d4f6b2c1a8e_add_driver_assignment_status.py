"""add driver assignment status

Revision ID: 9d4f6b2c1a8e
Revises: 7c2e1f9a6d4b
Create Date: 2026-03-28 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "9d4f6b2c1a8e"
down_revision = "7c2e1f9a6d4b"
branch_labels = None
depends_on = None


driver_assignment_status = postgresql.ENUM(
    "ACCEPTED",
    "REJECTED",
    name="driver_assignment_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    driver_assignment_status.create(bind, checkfirst=True)
    op.add_column(
        "driver_assignments",
        sa.Column("status", driver_assignment_status, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("driver_assignments", "status")

    bind = op.get_bind()
    driver_assignment_status.drop(bind, checkfirst=True)
