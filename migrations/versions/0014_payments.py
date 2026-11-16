# 用途：创建与企业账单关联的支付会话。
import sqlalchemy as sa
from alembic import op

revision = "0014_payments"
down_revision = "0013_invoice_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id"), nullable=False, unique=True
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_reference", sa.Uuid(), nullable=False, unique=True),
        sa.Column("expected_amount_cents", sa.Numeric(40, 0), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(10), server_default=sa.text("'pending'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending', 'failed', 'succeeded')", name="ck_payments_status"
        ),
        sa.CheckConstraint(
            "expected_amount_cents >= 0 AND currency = 'CNY'", name="ck_payments_amount"
        ),
    )


def downgrade() -> None:
    op.drop_table("payments")
