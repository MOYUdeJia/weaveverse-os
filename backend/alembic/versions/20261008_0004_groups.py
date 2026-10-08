"""Add groups and attach every existing nav item to the system group.

Revision ID: 20261008_0004
Revises: 20261007_0003
Create Date: 2026-10-08

Existing nav_items keep their ids, titles, icons, page types, sort order,
timestamps, and blocks. Books are untouched. A system group and its
group_overview page are inserted. New columns use defaults so SQLite can
add them without rebuilding nav_items.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261008_0004"
down_revision: Union[str, Sequence[str], None] = "20261007_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 写入 UTC 时间，和现有导航行一样不带时区信息。
# Store UTC without tzinfo, matching existing nav timestamps.
def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# 新建分组表，把现有导航全部挂到「系统」，并补一条导览页。
# Create groups, hang existing nav rows on 系统, and insert its overview.
def upgrade() -> None:
    now = _now()
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("icon", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_groups_is_system", "groups", ["is_system"], unique=False)
    op.create_index("ix_groups_sort_order", "groups", ["sort_order"], unique=False)
    op.create_index(
        "uq_groups_one_system",
        "groups",
        ["is_system"],
        unique=True,
        sqlite_where=sa.text("is_system = 1"),
    )

    groups = sa.table(
        "groups",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("icon", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        groups,
        [
            {
                "id": 1,
                "name": "系统",
                "icon": "⚙️",
                "description": "",
                "is_system": True,
                "sort_order": 0,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    # Alembic 会把 ForeignKey 拆成单独的 ALTER CONSTRAINT，SQLite 不支持。
    # 这里直接写 ALTER TABLE，让外键进表定义，已有行用 DEFAULT 1。
    # Alembic splits ForeignKey into ALTER CONSTRAINT, which SQLite rejects.
    # A raw ALTER TABLE keeps the foreign key and backfills existing rows with 1.
    op.execute("ALTER TABLE nav_items ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
    op.execute(
        "ALTER TABLE nav_items ADD COLUMN group_id INTEGER NOT NULL DEFAULT 1 "
        "REFERENCES groups (id) ON DELETE CASCADE"
    )
    op.create_index("ix_nav_items_group_id", "nav_items", ["group_id"], unique=False)
    op.create_index(
        "uq_nav_group_overview",
        "nav_items",
        ["group_id"],
        unique=True,
        sqlite_where=sa.text("page_type = 'group_overview'"),
    )

    nav_items = sa.table(
        "nav_items",
        sa.column("title", sa.String),
        sa.column("icon", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("page_type", sa.String),
        sa.column("group_id", sa.Integer),
        sa.column("pinned", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        nav_items,
        [
            {
                "title": "系统",
                "icon": "⚙️",
                "sort_order": 0,
                "page_type": "group_overview",
                "group_id": 1,
                "pinned": False,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


# 去掉导览页、分组外键和 groups 表。用户导航行保留。
# Remove overview rows, the group foreign key, and groups. User nav rows stay.
def downgrade() -> None:
    op.execute(
        "DELETE FROM blocks WHERE nav_item_id IN ("
        "SELECT id FROM nav_items WHERE page_type = 'group_overview')"
    )
    op.execute("DELETE FROM nav_items WHERE page_type = 'group_overview'")
    op.drop_index("uq_nav_group_overview", table_name="nav_items")
    op.drop_index("ix_nav_items_group_id", table_name="nav_items")
    op.drop_column("nav_items", "group_id")
    op.drop_column("nav_items", "pinned")
    op.drop_index("uq_groups_one_system", table_name="groups")
    op.drop_index("ix_groups_sort_order", table_name="groups")
    op.drop_index("ix_groups_is_system", table_name="groups")
    op.drop_table("groups")
