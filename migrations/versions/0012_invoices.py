# 用途：创建账期唯一的账单及整数分明细。
import sqlalchemy as sa
from alembic import op

revision = "0012_invoices"
down_revision = "0011_settlement_inputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("period_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version_id", sa.Uuid(), sa.ForeignKey("plan_versions.id"), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(8), server_default=sa.text("'open'"), nullable=False),
        sa.Column("base_fee_cents", sa.Numeric(40, 0), nullable=False),
        sa.Column("usage_fee_cents", sa.Numeric(40, 0), nullable=False),
        sa.Column("total_cents", sa.Numeric(40, 0), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["period_id", "tenant_id"], ["billing_periods.id", "billing_periods.tenant_id"]
        ),
        sa.CheckConstraint("status IN ('open', 'paid', 'void')", name="ck_invoices_status"),
        sa.CheckConstraint("currency = 'CNY'", name="ck_invoices_currency"),
        sa.CheckConstraint(
            "base_fee_cents >= 0 AND usage_fee_cents >= 0 "
            "AND total_cents = base_fee_cents + usage_fee_cents",
            name="ck_invoices_amounts",
        ),
    )
    op.create_index("ix_invoices_tenant_created", "invoices", ["tenant_id", "created_at", "id"])
    op.create_table(
        "invoice_items",
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id"), primary_key=True),
        sa.Column("kind", sa.String(8), primary_key=True),
        sa.Column("plan_version_id", sa.Uuid(), sa.ForeignKey("plan_versions.id"), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("unit_price_cents", sa.Numeric(40, 0), nullable=False),
        sa.Column("amount_cents", sa.Numeric(40, 0), nullable=False),
        sa.CheckConstraint("kind IN ('base', 'usage')", name="ck_invoice_items_kind"),
        sa.CheckConstraint(
            "quantity >= 0 AND unit_price_cents >= 0 "
            "AND amount_cents = quantity * unit_price_cents",
            name="ck_invoice_items_amount",
        ),
    )


def downgrade() -> None:
    op.drop_table("invoice_items")
    op.drop_table("invoices")
