# 用途：创建用量事件与额度桶，并用已有账期快照回填期初额度。
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_metering"
down_revision = "0007_subscription_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_billing_periods_id_tenant", "billing_periods", ["id", "tenant_id"]
    )
    op.create_table(
        "quota_buckets",
        sa.Column("tenant_id", sa.Uuid(), primary_key=True),
        sa.Column("period_id", sa.Uuid(), primary_key=True),
        sa.Column("metric", sa.String(32), primary_key=True),
        sa.Column("used", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("hard_limit", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["period_id", "tenant_id"],
            ["billing_periods.id", "billing_periods.tenant_id"],
            name="fk_quota_buckets_period_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("metric = 'data_query'", name="ck_quota_buckets_metric"),
        sa.CheckConstraint(
            "hard_limit > 0 AND used BETWEEN 0 AND hard_limit", name="ck_quota_buckets_bounds"
        ),
    )
    op.execute(
        """
        INSERT INTO quota_buckets (tenant_id, period_id, metric, used, hard_limit)
        SELECT p.tenant_id, p.id, 'data_query', 0, t.hard_limit
        FROM billing_periods AS p
        JOIN period_terms AS t ON t.period_id = p.id
        """
    )
    op.create_table(
        "usage_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("period_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result_snapshot", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "period_id", "metric"],
            ["quota_buckets.tenant_id", "quota_buckets.period_id", "quota_buckets.metric"],
            name="fk_usage_events_bucket",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "event_id", name="uq_usage_events_tenant_event"),
        sa.CheckConstraint("quantity BETWEEN 1 AND 1000000", name="ck_usage_events_quantity"),
    )
    op.create_index(
        "ix_usage_events_tenant_period_received",
        "usage_events",
        ["tenant_id", "period_id", "received_at"],
    )


def downgrade() -> None:
    op.drop_table("usage_events")
    op.drop_table("quota_buckets")
    op.drop_constraint("uq_billing_periods_id_tenant", "billing_periods", type_="unique")
