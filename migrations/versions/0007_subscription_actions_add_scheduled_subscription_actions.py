# 用途：增加订阅预约与到期取消字段，并约束预约字段完整性和取消优先规则。
"""add scheduled subscription actions

Revision ID: 0007_subscription_actions
Revises: 0006_subscriptions
Create Date: 2026-11-04 16:11:40.398773
"""

from collections.abc import Sequence

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

revision: str = "0007_subscription_actions"
down_revision: str | Sequence[str] | None = "0006_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("pending_plan_version_id", sa.Uuid(), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("pending_effective_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "cancel_at_period_end", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    op.add_column(
        "subscriptions", sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "subscriptions", sa.Column("cancel_effective_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "subscriptions", sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_subscriptions_pending_version",
        "subscriptions",
        "plan_versions",
        ["pending_plan_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_subscriptions_pending_pair",
        "subscriptions",
        "(pending_plan_version_id IS NULL) = (pending_effective_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_subscriptions_cancel_fields",
        "subscriptions",
        "NOT cancel_at_period_end OR "
        "(cancel_effective_at IS NOT NULL AND cancel_requested_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_subscriptions_cancel_priority",
        "subscriptions",
        "NOT cancel_at_period_end OR pending_plan_version_id IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_subscriptions_cancel_priority", "subscriptions", type_="check")
    op.drop_constraint("ck_subscriptions_cancel_fields", "subscriptions", type_="check")
    op.drop_constraint("ck_subscriptions_pending_pair", "subscriptions", type_="check")
    op.drop_constraint("fk_subscriptions_pending_version", "subscriptions", type_="foreignkey")
    op.drop_column("subscriptions", "canceled_at")
    op.drop_column("subscriptions", "cancel_effective_at")
    op.drop_column("subscriptions", "cancel_requested_at")
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_column("subscriptions", "pending_effective_at")
    op.drop_column("subscriptions", "pending_plan_version_id")
