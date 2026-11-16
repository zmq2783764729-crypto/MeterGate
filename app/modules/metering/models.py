# 用途：定义用量事件与额度桶，并在数据库约束租户归属、事件唯一性和额度边界。
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.metering.schemas import MAX_USAGE_QUANTITY


class QuotaBucket(Base):
    __tablename__ = "quota_buckets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["period_id", "tenant_id"],
            ["billing_periods.id", "billing_periods.tenant_id"],
            name="fk_quota_buckets_period_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("metric = 'data_query'", name="ck_quota_buckets_metric"),
        CheckConstraint(
            "hard_limit > 0 AND used BETWEEN 0 AND hard_limit", name="ck_quota_buckets_bounds"
        ),
    )
    tenant_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    period_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    metric: Mapped[str] = mapped_column(String(32), primary_key=True)
    used: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    hard_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "period_id", "metric"],
            ["quota_buckets.tenant_id", "quota_buckets.period_id", "quota_buckets.metric"],
            name="fk_usage_events_bucket",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "event_id", name="uq_usage_events_tenant_event"),
        CheckConstraint(
            f"quantity BETWEEN 1 AND {MAX_USAGE_QUANTITY}", name="ck_usage_events_quantity"
        ),
        Index("ix_usage_events_tenant_period_received", "tenant_id", "period_id", "received_at"),
        Index("ix_usage_events_tenant_timeline", "tenant_id", "received_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    event_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    period_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
