"""Add book notes and an EPUB locator on books.

Revision ID: 20261028_0013
Revises: 20261012_0012
Create Date: 2026-10-28
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261028_0013"
down_revision: Union[str, Sequence[str], None] = "20261012_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("books", sa.Column("progress_cfi", sa.Text(), nullable=False, server_default=""))
    op.create_table(
        "book_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("note_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_book_notes_book_id", "book_notes", ["book_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_book_notes_book_id", table_name="book_notes")
    op.drop_table("book_notes")
    op.drop_column("books", "progress_cfi")
