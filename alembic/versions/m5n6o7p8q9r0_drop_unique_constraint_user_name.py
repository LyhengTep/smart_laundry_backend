"""drop unique constraint on user_name

Revision ID: m5n6o7p8q9r0
Revises: l4m5n6o7p8q9
Create Date: 2026-05-04

"""
from alembic import op

revision = "m5n6o7p8q9r0"
down_revision = "l4m5n6o7p8q9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_users_user_name", table_name="users")
    op.create_index("ix_users_user_name", "users", ["user_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_user_name", table_name="users")
    op.create_index("ix_users_user_name", "users", ["user_name"], unique=True)
