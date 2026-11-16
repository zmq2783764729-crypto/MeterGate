# 用途：为企业跨账期的时间游标增加索引。
from alembic import op

revision = "0016_usage_timeline"
down_revision = "0015_payment_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_usage_events_tenant_timeline", "usage_events", ["tenant_id", "received_at", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_usage_events_tenant_timeline", table_name="usage_events")
