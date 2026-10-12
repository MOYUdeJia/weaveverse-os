"""Clear broken vault test rows once. The security password file is not touched.

Revision ID: 20261012_0012
Revises: 20261011_0011
Create Date: 2026-10-12
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20261012_0012"
down_revision: Union[str, Sequence[str], None] = "20261011_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM vault_entries")
    op.execute("DELETE FROM vault_sections")


def downgrade() -> None:
    pass
