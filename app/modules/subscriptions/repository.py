# 用途：按可信租户查询、锁定和写入订阅周期及条款，数据写入仅flush而不提交。
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import PlanVersion
from app.modules.subscriptions.models import BillingPeriod, PeriodTerms, Subscription
from app.modules.tenants.context import TenantContext


async def get_subscription(session: AsyncSession, context: TenantContext) -> Subscription | None:
    return await session.scalar(
        select(Subscription).where(Subscription.tenant_id == context.tenant_id)
    )


async def lock_subscription(session: AsyncSession, tenant_id: UUID) -> Subscription | None:
    return await session.scalar(
        select(Subscription).where(Subscription.tenant_id == tenant_id).with_for_update()
    )


async def lock_open_period(
    session: AsyncSession, tenant_id: UUID, subscription_id: UUID
) -> BillingPeriod | None:
    return await session.scalar(
        select(BillingPeriod)
        .where(
            BillingPeriod.tenant_id == tenant_id,
            BillingPeriod.subscription_id == subscription_id,
            BillingPeriod.status == "open",
        )
        .with_for_update()
    )


async def add_subscription(
    session: AsyncSession, context: TenantContext, version: PlanVersion, now: datetime
) -> Subscription:
    row = Subscription(
        tenant_id=context.tenant_id,
        plan_version_id=version.id,
        status="active",
        billing_anchor_day=now.day,
        activated_at=now,
    )
    session.add(row)
    await session.flush()
    return row


async def add_period(
    session: AsyncSession,
    subscription: Subscription,
    start: datetime,
    end: datetime,
) -> BillingPeriod:
    row = BillingPeriod(
        subscription_id=subscription.id,
        tenant_id=subscription.tenant_id,
        period_start=start,
        period_end=end,
        status="open",
    )
    session.add(row)
    await session.flush()
    return row


async def add_terms(
    session: AsyncSession, period: BillingPeriod, version: PlanVersion
) -> PeriodTerms:
    row = PeriodTerms(
        period_id=period.id,
        plan_version_id=version.id,
        currency=version.currency,
        billing_interval=version.billing_interval,
        base_fee_cents=version.base_fee_cents,
        unit_price_cents=version.unit_price_cents,
        hard_limit=version.hard_limit,
    )
    session.add(row)
    await session.flush()
    return row


async def get_open_period(
    session: AsyncSession, context: TenantContext, subscription_id: UUID
) -> BillingPeriod | None:
    return await session.scalar(
        select(BillingPeriod).where(
            BillingPeriod.tenant_id == context.tenant_id,
            BillingPeriod.subscription_id == subscription_id,
            BillingPeriod.status == "open",
        )
    )


async def get_terms(
    session: AsyncSession, context: TenantContext, period_id: UUID
) -> PeriodTerms | None:
    return await session.scalar(
        select(PeriodTerms)
        .join(BillingPeriod, PeriodTerms.period_id == BillingPeriod.id)
        .where(BillingPeriod.tenant_id == context.tenant_id, PeriodTerms.period_id == period_id)
    )
