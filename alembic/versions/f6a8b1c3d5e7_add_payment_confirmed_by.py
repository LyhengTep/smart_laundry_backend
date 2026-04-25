"""add payment confirmed_by

Revision ID: f6a8b1c3d5e7
Revises: e5f7a9b2c4d6
Create Date: 2026-04-22 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f6a8b1c3d5e7"
down_revision = "e5f7a9b2c4d6"
branch_labels = None
depends_on = None

confirmed_by_type = postgresql.ENUM(
    "DRIVER",
    "ADMIN",
    name="confirmed_by_type",
    create_type=False,
)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    confirmed_by_type.create(bind, checkfirst=True)

    if not _has_column("payments", "confirmed_by"):
        op.add_column(
            "payments",
            sa.Column("confirmed_by", confirmed_by_type, nullable=True),
        )


def downgrade() -> None:
    if _has_column("payments", "confirmed_by"):
        op.drop_column("payments", "confirmed_by")

    bind = op.get_bind()
    confirmed_by_type.drop(bind, checkfirst=True)
