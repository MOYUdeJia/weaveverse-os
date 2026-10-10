"""Add photo_library metadata table.

Revision ID: 20261010_0007
Revises: 20261010_0006
Create Date: 2026-10-10

Stores filenames that already live in attachments. Deleting a row does not
delete the file.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261010_0007"
down_revision: Union[str, Sequence[str], None] = "20261010_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photo_library",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_photo_library_filename", "photo_library", ["filename"], unique=True)
    op.create_index("ix_photo_library_added_at", "photo_library", ["added_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_photo_library_added_at", table_name="photo_library")
    op.drop_index("ix_photo_library_filename", table_name="photo_library")
    op.drop_table("photo_library")
