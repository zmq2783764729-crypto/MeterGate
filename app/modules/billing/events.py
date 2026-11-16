# 用途：将账期关闭转换为同事务的结算领域事件。
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscriptions.models import BillingPeriod
from app.workers.outbox import enqueue_domain_event

PERIOD_CLOSED = "billing.period_closed"


async def queue_period_closed(session: AsyncSession, period: BillingPeriod) -> None:
    await enqueue_domain_event(
        session,
        PERIOD_CLOSED,
        period.id,
        {"tenant_id": str(period.tenant_id), "period_id": str(period.id)},
    )
