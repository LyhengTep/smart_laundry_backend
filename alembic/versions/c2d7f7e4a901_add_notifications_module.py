"""add notifications module

Revision ID: c2d7f7e4a901
Revises: 8f3c1d2a4b5c
Create Date: 2026-03-18 00:15:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c2d7f7e4a901"
down_revision = "8f3c1d2a4b5c"
branch_labels = None
depends_on = None


notification_type = postgresql.ENUM(
    "ORDER_STATUS",
    "PAYMENT",
    "SYSTEM",
    name="notification_type",
    create_type=False,
)

notification_channel = postgresql.ENUM(
    "IN_APP",
    "PUSH",
    "EMAIL",
    "SMS",
    name="notification_channel",
    create_type=False,
)

notification_status = postgresql.ENUM(
    "PENDING",
    "SENT",
    "FAILED",
    "READ",
    name="notification_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    notification_type.create(bind, checkfirst=True)
    notification_channel.create(bind, checkfirst=True)
    notification_status.create(bind, checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(length=100), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_type"), "notifications", ["type"], unique=False)
    op.create_index(op.f("ix_notifications_reference_id"), "notifications", ["reference_id"], unique=False)
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)
    op.create_index(op.f("ix_notifications_status"), "notifications", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_status"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_read"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_reference_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")

    bind = op.get_bind()
    notification_status.drop(bind, checkfirst=True)
    notification_channel.drop(bind, checkfirst=True)
    notification_type.drop(bind, checkfirst=True)
