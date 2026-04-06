"""update driver assignment status enum

Revision ID: c6e8a1b4d2f7
Revises: a7c5e2d1f9b4
Create Date: 2026-04-06 00:00:01
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "c6e8a1b4d2f7"
down_revision = "a7c5e2d1f9b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum
                WHERE enumlabel = 'PICKED_UP'
                  AND enumtypid = 'driver_assignment_status'::regtype
            ) THEN
                ALTER TYPE driver_assignment_status ADD VALUE 'PICKED_UP';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum
                WHERE enumlabel = 'DELIVERED'
                  AND enumtypid = 'driver_assignment_status'::regtype
            ) THEN
                ALTER TYPE driver_assignment_status ADD VALUE 'DELIVERED';
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
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_assignment_status') THEN
                CREATE TYPE driver_assignment_status_old AS ENUM ('ACCEPTED', 'REJECTED');

                ALTER TABLE driver_assignments
                ALTER COLUMN status TYPE driver_assignment_status_old
                USING (
                    CASE
                        WHEN status::text IN ('PICKED_UP', 'DELIVERED') THEN 'ACCEPTED'
                        ELSE status::text
                    END
                )::driver_assignment_status_old;

                DROP TYPE driver_assignment_status;
                ALTER TYPE driver_assignment_status_old RENAME TO driver_assignment_status;
            END IF;
        END
        $$;
        """
    )
