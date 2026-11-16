# 用途：创建每个已关闭账期仅一条的后台结算输入。
import sqlalchemy as sa
from alembic import op

revision = "0011_settlement_inputs"
down_revision = "0010_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settlement_inputs",
        sa.Column(
            "period_id",
            sa.Uuid(),
            sa.ForeignKey("billing_periods.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("outbox_events.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("total_quantity", sa.BigInteger(), nullable=False),
        sa.Column(
            "processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("settlement_inputs")
