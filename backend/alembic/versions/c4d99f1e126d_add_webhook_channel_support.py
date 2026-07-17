"""add webhook channel support

Revision ID: c4d99f1e126d
Revises: ca053a55ea21
Create Date: 2026-07-17 18:57:13.332842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d99f1e126d'
down_revision: Union[str, None] = 'ca053a55ea21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("webhook_url", sa.String(length=500), nullable=True))

    reminder_channel = sa.Enum("email", "webhook", name="reminder_channel")
    reminder_channel.create(op.get_bind())
    op.add_column(
        "reminders",
        sa.Column("channel", reminder_channel, nullable=False, server_default="email"),
    )
    op.alter_column("reminders", "channel", server_default=None)


def downgrade() -> None:
    op.drop_column("reminders", "channel")
    sa.Enum(name="reminder_channel").drop(op.get_bind())
    op.drop_column("businesses", "webhook_url")
