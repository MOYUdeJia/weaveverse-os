"""Create the books table for the bookshelf.

Revision ID: 20261007_0003
Revises: 20261006_0002
Create Date: 2026-10-07

Additive only: nav_items and blocks are untouched.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261007_0003"
down_revision: Union[str, Sequence[str], None] = "20261006_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 新建 books 表，不改导航和区块。
# Create books without changing navigation or blocks.
def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("author", sa.String(length=500), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("cover_ext", sa.String(length=8), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("text_encoding", sa.String(length=32), nullable=False),
        sa.Column("chapter_count", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("toc", sa.Text(), server_default="[]", nullable=False),
        sa.Column("progress_chapter", sa.Integer(), nullable=False),
        sa.Column("progress_offset", sa.Float(), nullable=False),
        sa.Column("progress_ratio", sa.Float(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_books_format", "books", ["format"], unique=False)
    op.create_index("ix_books_last_read_at", "books", ["last_read_at"], unique=False)


# 只删除 books 表。
# Drop only the books table.
def downgrade() -> None:
    op.drop_index("ix_books_last_read_at", table_name="books")
    op.drop_index("ix_books_format", table_name="books")
    op.drop_table("books")
