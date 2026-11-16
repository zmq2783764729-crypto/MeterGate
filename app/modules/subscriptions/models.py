# 用途：定义订阅、周期和不可变条款快照，约束套餐预约与到期取消字段及租户归属。
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_subscriptions_tenant"),
        UniqueConstraint("id", "tenant_id", name="uq_subscriptions_id_tenant"),
        CheckConstraint("status IN ('active', 'canceled')", name="ck_subscriptions_status"),
        CheckConstraint("billing_anchor_day BETWEEN 1 AND 31", name="ck_subscriptions_anchor"),
        CheckConstraint(
            "(pending_plan_version_id IS NULL) = (pending_effective_at IS NULL)",
            name="ck_subscriptions_pending_pair",
        ),
        CheckConstraint(
            "NOT cancel_at_period_end OR "
            "(cancel_effective_at IS NOT NULL AND cancel_requested_at IS NOT NULL)",
            name="ck_subscriptions_cancel_fields",
        ),
        CheckConstraint(
            "NOT cancel_at_period_end OR pending_plan_version_id IS NULL",
            name="ck_subscriptions_cancel_priority",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("plan_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    billing_anchor_day: Mapped[int] = mapped_column(Integer, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pending_plan_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plan_versions.id", ondelete="RESTRICT", name="fk_subscriptions_pending_version")
    )
    pending_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BillingPeriod(Base):
    __tablename__ = "billing_periods"
    __table_args__ = (
        ForeignKeyConstraint(
            ["subscription_id", "tenant_id"],
            ["subscriptions.id", "subscriptions.tenant_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("subscription_id", "period_start", name="uq_billing_periods_start"),
        UniqueConstraint("id", "tenant_id", name="uq_billing_periods_id_tenant"),
        CheckConstraint("period_end > period_start", name="ck_billing_periods_range"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_billing_periods_status"),
        Index(
            "uq_billing_periods_one_open",
            "subscription_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    subscription_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class PeriodTerms(Base):
    __tablename__ = "period_terms"
    __table_args__ = (
        CheckConstraint(
            "base_fee_cents >= 0 AND unit_price_cents >= 0", name="ck_period_terms_prices"
        ),
        CheckConstraint("hard_limit > 0", name="ck_period_terms_limit"),
        CheckConstraint(
            "currency = 'CNY' AND billing_interval = 'month'", name="ck_period_terms_fixed"
        ),
    )
    period_id: Mapped[UUID] = mapped_column(
        ForeignKey("billing_periods.id", ondelete="RESTRICT"), primary_key=True
    )
    plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("plan_versions.id", ondelete="RESTRICT"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(8), nullable=False)
    base_fee_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hard_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)
