"""Add password vault tables.

Revision ID: 20261011_0011
Revises: 20261010_0010
Create Date: 2026-10-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261011_0011"
down_revision: Union[str, Sequence[str], None] = "20261010_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vault_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_sections_sort_order", "vault_sections", ["sort_order"], unique=False)
    op.create_table(
        "vault_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("username", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("password_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["vault_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_entries_section_id", "vault_entries", ["section_id"], unique=False)
    op.create_index("ix_vault_entries_sort_order", "vault_entries", ["sort_order"], unique=False)
    op.create_index("ix_vault_entries_pinned", "vault_entries", ["pinned"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vault_entries_pinned", table_name="vault_entries")
    op.drop_index("ix_vault_entries_sort_order", table_name="vault_entries")
    op.drop_index("ix_vault_entries_section_id", table_name="vault_entries")
    op.drop_table("vault_entries")
    op.drop_index("ix_vault_sections_sort_order", table_name="vault_sections")
    op.drop_table("vault_sections")
