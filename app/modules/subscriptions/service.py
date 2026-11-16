# 用途：事务化开通订阅与首期额度桶，处理套餐预约、到期取消和消费前置校验。
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.api_keys.context import ApiKeyContext
from app.modules.audit.service import record_audit
from app.modules.catalog.models import PlanVersion
from app.modules.metering.repository import add_quota_bucket
from app.modules.subscriptions import repository
from app.modules.subscriptions.models import BillingPeriod, Subscription
from app.modules.subscriptions.period_service import close_period, finish_cancellation
from app.modules.subscriptions.periods import next_month_boundary, utc_now
from app.modules.subscriptions.schemas import (
    BillingPeriodPublic,
    PeriodTermsPublic,
    SubscriptionActivateRequest,
    SubscriptionPlanChangeRequest,
    SubscriptionPublic,
)
from app.modules.subscriptions.transitions import can_consume, ensure_change_allowed
from app.modules.tenants.authorization import lock_and_authorize_admin
from app.modules.tenants.context import TenantContext


async def subscription_public(
    session: AsyncSession, context: TenantContext, subscription: Subscription
) -> SubscriptionPublic:
    period = await repository.get_open_period(session, context, subscription.id)
    public_period = None
    if period is not None:
        terms = await repository.get_terms(session, context, period.id)
        if terms is None:
            raise DomainError("SUBSCRIPTION_INCONSISTENT", "订阅周期数据异常，请联系管理员", 500)
        public_period = BillingPeriodPublic(
            id=period.id,
            period_start=period.period_start,
            period_end=period.period_end,
            status=period.status,
            terms=PeriodTermsPublic.model_validate(terms),
        )
    elif subscription.status == "active":
        raise DomainError("SUBSCRIPTION_INCONSISTENT", "订阅周期数据异常，请联系管理员", 500)
    return SubscriptionPublic(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan_version_id=subscription.plan_version_id,
        status=subscription.status,
        billing_anchor_day=subscription.billing_anchor_day,
        activated_at=subscription.activated_at,
        current_period=public_period,
        pending_plan_version_id=subscription.pending_plan_version_id,
        pending_effective_at=subscription.pending_effective_at,
        cancel_at_period_end=subscription.cancel_at_period_end,
        cancel_requested_at=subscription.cancel_requested_at,
        cancel_effective_at=subscription.cancel_effective_at,
        canceled_at=subscription.canceled_at,
        can_consume=period is not None
        and can_consume(
            status=subscription.status,
            cancel_pending=subscription.cancel_at_period_end,
            cancel_effective_at=subscription.cancel_effective_at,
            period_start=period.period_start,
            period_end=period.period_end,
            now=utc_now(),
        ),
    )


async def activate_subscription(
    session: AsyncSession, context: TenantContext, data: SubscriptionActivateRequest
) -> SubscriptionPublic:
    try:
        async with session.begin():
            await lock_and_authorize_admin(session, context)
            if await repository.get_subscription(session, context) is not None:
                raise DomainError("SUBSCRIPTION_EXISTS", "该企业已存在订阅", 409)
            version = await session.get(PlanVersion, data.plan_version_id)
            if version is None:
                raise DomainError("PLAN_VERSION_NOT_FOUND", "套餐价格版本不存在", 404)
            now = utc_now().astimezone(UTC)
            subscription = await repository.add_subscription(session, context, version, now)
            period = await repository.add_period(
                session,
                subscription,
                now,
                next_month_boundary(now, subscription.billing_anchor_day),
            )
            terms = await repository.add_terms(session, period, version)
            await add_quota_bucket(
                session,
                tenant_id=period.tenant_id,
                period_id=period.id,
                hard_limit=terms.hard_limit,
            )
            result = await subscription_public(session, context, subscription)
        return result
    except IntegrityError as exc:
        if (
            getattr(getattr(exc.orig, "__cause__", None), "constraint_name", None)
            == "uq_subscriptions_tenant"
        ):
            raise DomainError("SUBSCRIPTION_EXISTS", "该企业已存在订阅", 409) from exc
        raise


async def get_subscription(session: AsyncSession, context: TenantContext) -> SubscriptionPublic:
    # 读取时仅结算已经到期的取消，不续期、不把预约套餐应用到新周期。
    async with session.begin():
        subscription = await _locked_subscription(session, context)
        await _finalize_due_cancellation(session, context, subscription, utc_now())
        result = await subscription_public(session, context, subscription)
    return result


async def _locked_subscription(
    session: AsyncSession, context: TenantContext | ApiKeyContext
) -> Subscription:
    subscription = await repository.lock_subscription(session, context.tenant_id)
    if subscription is None:
        raise DomainError("SUBSCRIPTION_NOT_FOUND", "该企业尚未开通订阅", 404)
    return subscription


async def _finalize_due_cancellation(
    session: AsyncSession, context: TenantContext, subscription: Subscription, now: datetime
) -> None:
    if (
        subscription.status == "active"
        and subscription.cancel_at_period_end
        and subscription.cancel_effective_at is not None
        and now >= subscription.cancel_effective_at
    ):
        period = await repository.lock_open_period(session, context.tenant_id, subscription.id)
        if period is not None:
            await close_period(
                session, period, reason="cancellation", actor_user_id=context.user_id
            )
        finish_cancellation(subscription)
        await session.flush()


async def schedule_plan_change(
    session: AsyncSession, context: TenantContext, data: SubscriptionPlanChangeRequest
) -> SubscriptionPublic:
    async with session.begin():
        await lock_and_authorize_admin(session, context)
        subscription = await _locked_subscription(session, context)
        # 不先写到期取消再抛错误，避免业务错误回滚带来“已写入”的错误承诺。
        ensure_change_allowed(subscription.status, subscription.cancel_at_period_end)
        period = await repository.lock_open_period(session, context.tenant_id, subscription.id)
        if period is None or utc_now() >= period.period_end:
            raise DomainError("PERIOD_ENDED", "本周期已结束，待周期轮转后再预约变更", 409)
        if data.plan_version_id == subscription.plan_version_id:
            raise DomainError("PLAN_ALREADY_CURRENT", "请选择与当前订阅不同的价格版本", 409)
        if await session.get(PlanVersion, data.plan_version_id) is None:
            raise DomainError("PLAN_VERSION_NOT_FOUND", "套餐价格版本不存在", 404)
        subscription.pending_plan_version_id = data.plan_version_id
        subscription.pending_effective_at = period.period_end
        record_audit(
            session,
            context.tenant_id,
            "subscription.plan_change_scheduled",
            subscription.id,
            actor_user_id=context.user_id,
            details={"plan_version_id": str(data.plan_version_id)},
        )
        await session.flush()
        result = await subscription_public(session, context, subscription)
    return result


async def cancel_at_period_end(session: AsyncSession, context: TenantContext) -> SubscriptionPublic:
    async with session.begin():
        await lock_and_authorize_admin(session, context)
        subscription = await _locked_subscription(session, context)
        now = utc_now()
        if subscription.status == "active" and not subscription.cancel_at_period_end:
            period = await repository.lock_open_period(session, context.tenant_id, subscription.id)
            if period is None:
                raise DomainError(
                    "SUBSCRIPTION_INCONSISTENT", "订阅周期数据异常，请联系管理员", 500
                )
            subscription.cancel_at_period_end = True
            subscription.cancel_requested_at = now
            subscription.cancel_effective_at = period.period_end
            subscription.pending_plan_version_id = None
            subscription.pending_effective_at = None
            record_audit(
                session,
                context.tenant_id,
                "subscription.cancellation_scheduled",
                subscription.id,
                actor_user_id=context.user_id,
            )
            await session.flush()
        elif subscription.status not in {"active", "canceled"}:
            raise DomainError("INVALID_SUBSCRIPTION_STATE", "当前订阅状态不允许取消", 409)
        await _finalize_due_cancellation(session, context, subscription, now)
        result = await subscription_public(session, context, subscription)
    return result


async def require_consumable_period(
    session: AsyncSession, context: TenantContext | ApiKeyContext, *, at: datetime | None = None
) -> BillingPeriod:
    """调用方必须持有外层事务；锁会保留到后续业务写入一起提交或回滚。"""
    if not session.in_transaction():
        raise RuntimeError("消费前置校验必须在调用方事务内执行")
    subscription = await _locked_subscription(session, context)
    period = await repository.lock_open_period(session, context.tenant_id, subscription.id)
    if period is None or not can_consume(
        status=subscription.status,
        cancel_pending=subscription.cancel_at_period_end,
        cancel_effective_at=subscription.cancel_effective_at,
        period_start=period.period_start,
        period_end=period.period_end,
        now=at if at is not None else utc_now(),
    ):
        raise DomainError("SUBSCRIPTION_NOT_CONSUMABLE", "订阅已取消或不在可消费周期内", 409)
    return period
