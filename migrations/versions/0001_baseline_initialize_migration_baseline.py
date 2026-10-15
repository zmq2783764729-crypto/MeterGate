# 用途：initialize migration baseline；记录本次表结构升级与回退操作。
"""initialize migration baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-15 09:33:07.203335
"""

from collections.abc import Sequence

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

revision: str = "0001_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
