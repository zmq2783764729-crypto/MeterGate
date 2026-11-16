# 用途：为支付回调创建提供方与事件编号级的幂等记录。
import sqlalchemy as sa
from alembic import op

revision = "0015_payment_events"
down_revision = "0014_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column("provider", sa.String(20), primary_key=True),
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])


def downgrade() -> None:
    op.drop_table("payment_events")
