"""Store focus-page tags on nav items.

Revision ID: 20261010_0006
Revises: 20261008_0005
Create Date: 2026-10-10

Tags are a JSON list in TEXT. Existing rows start as [].
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261010_0006"
down_revision: Union[str, Sequence[str], None] = "20261008_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "nav_items",
        sa.Column("tags", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("nav_items", "tags")
