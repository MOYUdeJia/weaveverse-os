"""Add nav_items.page_type and create the blocks table.

Revision ID: 20261006_0002
Revises: 20261006_0001
Create Date: 2026-10-06

This revision is additive only: it does not drop or recreate nav_items.
Existing rows keep their ids, titles, icons, sort_order, and timestamps.
SQLite does not enforce VARCHAR length, so icon max_length 8→20 is a
model/validation change only and is intentionally omitted from DDL.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0002"
down_revision: Union[str, Sequence[str], None] = "20261006_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 给现有导航加 page_type，并新建 blocks 表；不重建 nav_items。
# Add page_type to existing nav rows and create blocks without rebuilding nav_items.
def upgrade() -> None:
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nav_item_id", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), server_default="{}", nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["nav_item_id"], ["nav_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blocks_nav_item_id", "blocks", ["nav_item_id"], unique=False)
    op.create_index("ix_blocks_sort_order", "blocks", ["sort_order"], unique=False)

    op.add_column(
        "nav_items",
        sa.Column(
            "page_type",
            sa.String(length=50),
            nullable=False,
            server_default="markdown",
        ),
    )
    op.create_index("ix_nav_items_page_type", "nav_items", ["page_type"], unique=False)


# 撤销 page_type 与 blocks；不删除 nav_items 行。
# Undo page_type and blocks; do not delete nav_items rows.
def downgrade() -> None:
    op.drop_index("ix_nav_items_page_type", table_name="nav_items")
    op.drop_column("nav_items", "page_type")
    op.drop_index("ix_blocks_sort_order", table_name="blocks")
    op.drop_index("ix_blocks_nav_item_id", table_name="blocks")
    op.drop_table("blocks")
