"""add payment assignment_id

Revision ID: a2b4c6d8e1f3
Revises: f6a8b1c3d5e7
Create Date: 2026-04-22 00:00:02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a2b4c6d8e1f3"
down_revision = "f6a8b1c3d5e7"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("payments", "assignment_id"):
        op.add_column(
            "payments",
            sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_payments_assignment_id",
            "payments",
            "driver_assignments",
            ["assignment_id"],
            ["id"],
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_payments_assignment_id ON payments (assignment_id)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_payments_assignment_id")
    op.drop_constraint("fk_payments_assignment_id", "payments", type_="foreignkey")
    if _has_column("payments", "assignment_id"):
        op.drop_column("payments", "assignment_id")
