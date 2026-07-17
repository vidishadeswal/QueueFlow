"""drop failed from reminder_status enum

Revision ID: ca053a55ea21
Revises: 88b342c70c0e
Create Date: 2026-07-17 17:22:21.899306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca053a55ea21'
down_revision: Union[str, None] = '88b342c70c0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres has no direct "drop enum value" DDL, so recreate the type without
    # it and swap the column over. Safe here because no row has ever had
    # status='failed' -- the worker only ever writes 'pending' or 'dead_letter'
    # on a failed send, never 'failed' itself.
    op.execute("ALTER TYPE reminder_status RENAME TO reminder_status_old")
    op.execute("CREATE TYPE reminder_status AS ENUM ('pending', 'queued', 'sent', 'dead_letter')")
    op.execute(
        "ALTER TABLE reminders ALTER COLUMN status TYPE reminder_status "
        "USING status::text::reminder_status"
    )
    op.execute("DROP TYPE reminder_status_old")


def downgrade() -> None:
    op.execute("ALTER TYPE reminder_status RENAME TO reminder_status_new")
    op.execute("CREATE TYPE reminder_status AS ENUM ('pending', 'queued', 'sent', 'failed', 'dead_letter')")
    op.execute(
        "ALTER TABLE reminders ALTER COLUMN status TYPE reminder_status "
        "USING status::text::reminder_status"
    )
    op.execute("DROP TYPE reminder_status_new")
