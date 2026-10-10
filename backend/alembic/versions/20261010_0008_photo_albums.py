"""Add photo albums and per-photo display name.

Revision ID: 20261010_0008
Revises: 20261010_0007
Create Date: 2026-10-10

Existing photos stay uncategorized (album_id is null).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261010_0008"
down_revision: Union[str, Sequence[str], None] = "20261010_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photo_albums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("cover_filename", sa.String(length=255), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_photo_albums_sort_order", "photo_albums", ["sort_order"], unique=False)
    op.add_column(
        "photo_library",
        sa.Column("display_name", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "photo_library",
        sa.Column("album_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_photo_library_album_id", "photo_library", ["album_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_photo_library_album_id", table_name="photo_library")
    op.drop_column("photo_library", "album_id")
    op.drop_column("photo_library", "display_name")
    op.drop_index("ix_photo_albums_sort_order", table_name="photo_albums")
    op.drop_table("photo_albums")
