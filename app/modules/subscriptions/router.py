# 用途：为main.py提供订阅开通、预约、取消和读取处理，复用可信租户与管理员依赖。
from app.modules.subscriptions.schemas import (
    SubscriptionActivateRequest,
    SubscriptionPlanChangeRequest,
    SubscriptionPublic,
)
from app.modules.subscriptions.service import (
    activate_subscription,
    cancel_at_period_end,
    get_subscription,
    schedule_plan_change,
)
from app.modules.tenants.router import (
    AdminTenantDependency,
    TenantContextDependency,
    TenantSessionDependency,
)


async def activate(
    data: SubscriptionActivateRequest,
    context: AdminTenantDependency,
    session: TenantSessionDependency,
) -> SubscriptionPublic:
    return await activate_subscription(session, context, data)


async def read(
    context: TenantContextDependency, session: TenantSessionDependency
) -> SubscriptionPublic:
    return await get_subscription(session, context)


async def schedule(
    data: SubscriptionPlanChangeRequest,
    context: AdminTenantDependency,
    session: TenantSessionDependency,
) -> SubscriptionPublic:
    return await schedule_plan_change(session, context, data)


async def cancel(
    context: AdminTenantDependency, session: TenantSessionDependency
) -> SubscriptionPublic:
    return await cancel_at_period_end(session, context)
