"""Add system_config table

Revision ID: 002
Revises: 001
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_config",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Seed the global_write_enabled flag
    op.execute(
        "INSERT INTO system_config (key, value) VALUES ('global_write_enabled', 'true')"
    )
    op.execute(
        "INSERT INTO system_config (key, value) VALUES ('last_admin_heartbeat', now()::text)"
    )


def downgrade() -> None:
    op.drop_table("system_config")
