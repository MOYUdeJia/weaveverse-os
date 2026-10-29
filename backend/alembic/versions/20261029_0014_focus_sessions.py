"""Store finished focus intervals for the timeline.

Revision ID: 20261029_0014
Revises: 20261028_0013
Create Date: 2026-10-29
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261029_0014"
down_revision: Union[str, Sequence[str], None] = "20261028_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "focus_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_focus_sessions_completed_at", "focus_sessions", ["completed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_focus_sessions_completed_at", table_name="focus_sessions")
    op.drop_table("focus_sessions")
