# 用途：创建事务 Outbox、发布重试索引并补录已关闭账期。
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010_outbox"
down_revision = "0009_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("topic", sa.String(60), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(100)),
        sa.UniqueConstraint("topic", "aggregate_id", name="uq_outbox_topic_aggregate"),
    )
    op.create_index(
        "ix_outbox_ready",
        "outbox_events",
        ["next_attempt_at", "id"],
        postgresql_where=sa.text("published_at IS NULL AND failed_at IS NULL"),
    )
    op.execute(
        """
        INSERT INTO outbox_events (id, topic, aggregate_id, payload)
        SELECT gen_random_uuid(), 'billing.period_closed', id,
               jsonb_build_object('tenant_id', tenant_id, 'period_id', id)
        FROM billing_periods WHERE status = 'closed'
        """
    )


def downgrade() -> None:
    op.drop_table("outbox_events")
