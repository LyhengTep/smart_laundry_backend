"""fix driver assignment role enum name

Revision ID: e1b7c9d4a2f3
Revises: 9d4f6b2c1a8e
Create Date: 2026-03-29 00:00:01
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "e1b7c9d4a2f3"
down_revision = "9d4f6b2c1a8e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'darole')
               AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_assignment_role') THEN
                ALTER TYPE darole RENAME TO driver_assignment_role;
            ELSIF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'darole')
               AND EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_assignment_role') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'driver_assignments' AND column_name = 'role') THEN
                    ALTER TABLE driver_assignments
                    ALTER COLUMN role TYPE driver_assignment_role
                    USING role::text::driver_assignment_role;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'driver_assignment_histories' AND column_name = 'role') THEN
                    ALTER TABLE driver_assignment_histories
                    ALTER COLUMN role TYPE driver_assignment_role
                    USING role::text::driver_assignment_role;
                END IF;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_assignment_role')
               AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'darole') THEN
                ALTER TYPE driver_assignment_role RENAME TO darole;
            ELSIF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_assignment_role')
               AND EXISTS (SELECT 1 FROM pg_type WHERE typname = 'darole') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'driver_assignments' AND column_name = 'role') THEN
                    ALTER TABLE driver_assignments
                    ALTER COLUMN role TYPE darole
                    USING role::text::darole;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'driver_assignment_histories' AND column_name = 'role') THEN
                    ALTER TABLE driver_assignment_histories
                    ALTER COLUMN role TYPE darole
                    USING role::text::darole;
                END IF;
            END IF;
        END
        $$;
        """
    )
