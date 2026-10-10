"""Add a display color to photo albums.

Revision ID: 20261010_0009
Revises: 20261010_0008
Create Date: 2026-10-10

Existing albums start with an empty color. The app fills one in when listed.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261010_0009"
down_revision: Union[str, Sequence[str], None] = "20261010_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "photo_albums",
        sa.Column("color", sa.String(length=16), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("photo_albums", "color")
