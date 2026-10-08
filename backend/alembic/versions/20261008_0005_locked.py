"""Add locked flags to groups and nav items.

Revision ID: 20261008_0005
Revises: 20261008_0004
Create Date: 2026-10-08

Existing rows stay unlocked. SQLite accepts a NOT NULL boolean with a
constant default, so the tables do not need to be rebuilt.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261008_0005"
down_revision: Union[str, Sequence[str], None] = "20261008_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "groups",
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "nav_items",
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("nav_items", "locked")
    op.drop_column("groups", "locked")
