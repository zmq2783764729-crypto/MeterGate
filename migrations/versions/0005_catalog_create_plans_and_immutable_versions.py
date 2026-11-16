# 用途：创建套餐和价格版本表，并以数据库触发器禁止修改、删除或清空历史版本。
"""create plans and immutable versions

Revision ID: 0005_catalog
Revises: 0004_api_keys
Create Date: 2026-11-02 10:45:22.092449
"""

from collections.abc import Sequence

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

revision: str = "0005_catalog"
down_revision: str | Sequence[str] | None = "0004_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "plan_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("billing_interval", sa.String(length=8), nullable=False),
        sa.Column("base_fee_cents", sa.BigInteger(), nullable=False),
        sa.Column("unit_price_cents", sa.BigInteger(), nullable=False),
        sa.Column("hard_limit", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "currency = 'CNY' AND billing_interval = 'month'", name="ck_plan_versions_terms"
        ),
        sa.CheckConstraint(
            "base_fee_cents >= 0 AND unit_price_cents >= 0", name="ck_plan_versions_prices"
        ),
        sa.CheckConstraint("hard_limit > 0", name="ck_plan_versions_limit"),
        sa.CheckConstraint("version > 0", name="ck_plan_versions_version"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "version", name="uq_plan_versions_plan_version"),
    )
    # 价格版本只允许INSERT；语句级触发器也保护TRUNCATE及批量SQL。
    op.execute("""
        CREATE FUNCTION reject_plan_version_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'plan versions are immutable; insert a new version'
                USING ERRCODE = '55000';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER protect_plan_versions
        BEFORE UPDATE OR DELETE OR TRUNCATE ON plan_versions
        FOR EACH STATEMENT EXECUTE FUNCTION reject_plan_version_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS protect_plan_versions ON plan_versions")
    op.execute("DROP FUNCTION IF EXISTS reject_plan_version_mutation()")
    op.drop_table("plan_versions")
    op.drop_table("plans")
