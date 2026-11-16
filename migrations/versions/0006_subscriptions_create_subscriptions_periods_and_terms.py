# 用途：创建企业订阅、计费周期和不可变条款快照，保护企业唯一订阅与单个开放周期。
"""create subscriptions periods and terms

Revision ID: 0006_subscriptions
Revises: 0005_catalog
Create Date: 2026-11-02 15:51:16.001836
"""

from collections.abc import Sequence

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

revision: str = "0006_subscriptions"
down_revision: str | Sequence[str] | None = "0005_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("billing_anchor_day", sa.Integer(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'canceled')", name="ck_subscriptions_status"),
        sa.CheckConstraint("billing_anchor_day BETWEEN 1 AND 31", name="ck_subscriptions_anchor"),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_subscriptions_id_tenant"),
        sa.UniqueConstraint("tenant_id", name="uq_subscriptions_tenant"),
    )
    op.create_table(
        "billing_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_billing_periods_status"),
        sa.CheckConstraint("period_end > period_start", name="ck_billing_periods_range"),
        sa.ForeignKeyConstraint(
            ["subscription_id", "tenant_id"],
            ["subscriptions.id", "subscriptions.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subscription_id", "period_start", name="uq_billing_periods_start"),
    )
    op.create_index(
        op.f("ix_billing_periods_tenant_id"), "billing_periods", ["tenant_id"], unique=False
    )
    op.create_index(
        "uq_billing_periods_one_open",
        "billing_periods",
        ["subscription_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_table(
        "period_terms",
        sa.Column("period_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("billing_interval", sa.String(length=8), nullable=False),
        sa.Column("base_fee_cents", sa.BigInteger(), nullable=False),
        sa.Column("unit_price_cents", sa.BigInteger(), nullable=False),
        sa.Column("hard_limit", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "currency = 'CNY' AND billing_interval = 'month'", name="ck_period_terms_fixed"
        ),
        sa.CheckConstraint(
            "base_fee_cents >= 0 AND unit_price_cents >= 0", name="ck_period_terms_prices"
        ),
        sa.CheckConstraint("hard_limit > 0", name="ck_period_terms_limit"),
        sa.ForeignKeyConstraint(["period_id"], ["billing_periods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("period_id"),
    )
    op.execute("""
        CREATE FUNCTION reject_period_terms_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'period terms are immutable' USING ERRCODE = '55000';
        END; $$
    """)
    op.execute("""
        CREATE TRIGGER protect_period_terms
        BEFORE UPDATE OR DELETE OR TRUNCATE ON period_terms
        FOR EACH STATEMENT EXECUTE FUNCTION reject_period_terms_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS protect_period_terms ON period_terms")
    op.execute("DROP FUNCTION IF EXISTS reject_period_terms_mutation()")
    op.drop_table("period_terms")
    op.drop_index(
        "uq_billing_periods_one_open",
        table_name="billing_periods",
        postgresql_where=sa.text("status = 'open'"),
    )
    op.drop_index(op.f("ix_billing_periods_tenant_id"), table_name="billing_periods")
    op.drop_table("billing_periods")
    op.drop_table("subscriptions")
