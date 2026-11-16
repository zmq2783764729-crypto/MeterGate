# 用途：锁定订阅及账期，关闭到期账期并应用预约续期或取消。
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import record_audit
from app.modules.billing.events import queue_period_closed
from app.modules.catalog.models import PlanVersion
from app.modules.metering.repository import add_quota_bucket
from app.modules.subscriptions import repository
from app.modules.subscriptions.models import BillingPeriod, Subscription
from app.modules.subscriptions.periods import contains_instant, next_month_boundary


async def close_period(
    session: AsyncSession,
    period: BillingPeriod,
    *,
    reason: str,
    actor_user_id: UUID | None = None,
) -> None:
    """调用方先锁订阅行和开放账期行。"""
    if period.status != "open":
        return
    period.status = "closed"
    await session.flush()
    await queue_period_closed(session, period)
    record_audit(
        session,
        period.tenant_id,
        "period.closed",
        period.id,
        actor_user_id=actor_user_id,
        details={"reason": reason},
    )


def finish_cancellation(subscription: Subscription) -> None:
    subscription.status = "canceled"
    subscription.canceled_at = subscription.cancel_effective_at
    subscription.pending_plan_version_id = None
    subscription.pending_effective_at = None


async def resolve_open_period(
    session: AsyncSession, tenant_id: UUID, now: datetime
) -> BillingPeriod | None:
    if not session.in_transaction() or now.utcoffset() is None:
        raise RuntimeError("账期轮转需要业务事务和带时区的当前时间")
    now = now.astimezone(UTC)
    subscription = await repository.lock_subscription(session, tenant_id)
    if subscription is None:
        raise DomainError("SUBSCRIPTION_NOT_FOUND", "该企业尚未开通订阅", 404)
    if subscription.status != "active":
        return None
    period = await repository.lock_open_period(session, tenant_id, subscription.id)
    if period is None:
        raise DomainError("SUBSCRIPTION_INCONSISTENT", "订阅周期数据异常，请联系管理员", 500)

    while now >= period.period_end:
        start = period.period_end
        cancel_at = subscription.cancel_effective_at
        if subscription.cancel_at_period_end and cancel_at is not None and cancel_at <= start:
            await close_period(session, period, reason="cancellation")
            finish_cancellation(subscription)
            return None

        await close_period(session, period, reason="renewal")
        if (
            subscription.pending_plan_version_id is not None
            and subscription.pending_effective_at is not None
            and subscription.pending_effective_at <= start
        ):
            subscription.plan_version_id = subscription.pending_plan_version_id
            subscription.pending_plan_version_id = None
            subscription.pending_effective_at = None

        version = await session.get(PlanVersion, subscription.plan_version_id)
        if version is None:
            raise DomainError("SUBSCRIPTION_INCONSISTENT", "订阅价格版本不存在", 500)
        period = await repository.add_period(
            session,
            subscription,
            start,
            next_month_boundary(start, subscription.billing_anchor_day),
        )
        terms = await repository.add_terms(session, period, version)
        await add_quota_bucket(
            session, tenant_id=tenant_id, period_id=period.id, hard_limit=terms.hard_limit
        )

    return period if contains_instant(period.period_start, period.period_end, now) else None
