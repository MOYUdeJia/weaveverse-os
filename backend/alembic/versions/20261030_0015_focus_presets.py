"""Tomato presets, and a place to keep abandoned rounds.

Revision ID: 20261030_0015
Revises: 20261029_0014
Create Date: 2026-10-30
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261030_0015"
down_revision: Union[str, Sequence[str], None] = "20261029_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("focus_sessions", sa.Column("category", sa.String(length=20), nullable=False, server_default=""))
    op.add_column("focus_sessions", sa.Column("outcome", sa.String(length=20), nullable=False, server_default="done"))
    op.add_column("focus_sessions", sa.Column("interrupt", sa.String(length=40), nullable=False, server_default=""))
    op.create_table(
        "focus_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("focus_minutes", sa.Integer(), nullable=False),
        sa.Column("rest_minutes", sa.Integer(), nullable=False),
        sa.Column("cycles", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_focus_presets_sort_order", "focus_presets", ["sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_focus_presets_sort_order", table_name="focus_presets")
    op.drop_table("focus_presets")
    op.drop_column("focus_sessions", "interrupt")
    op.drop_column("focus_sessions", "outcome")
    op.drop_column("focus_sessions", "category")
