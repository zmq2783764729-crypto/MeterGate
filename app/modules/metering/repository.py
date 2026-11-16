# 用途：初始化额度桶，以条件更新原子扣量，并按企业查询幂等记录。
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.metering.models import QuotaBucket, UsageEvent


async def add_quota_bucket(
    session: AsyncSession, *, tenant_id: UUID, period_id: UUID, hard_limit: int
) -> QuotaBucket:
    bucket = QuotaBucket(
        tenant_id=tenant_id, period_id=period_id, metric="data_query", used=0, hard_limit=hard_limit
    )
    session.add(bucket)
    await session.flush()
    return bucket


async def get_usage_event(
    session: AsyncSession, tenant_id: UUID, event_id: UUID
) -> UsageEvent | None:
    return await session.scalar(
        select(UsageEvent).where(UsageEvent.tenant_id == tenant_id, UsageEvent.event_id == event_id)
    )


async def debit_quota(
    session: AsyncSession, tenant_id: UUID, period_id: UUID, metric: str, quantity: int
) -> tuple[int, int] | None:
    result = await session.execute(
        update(QuotaBucket)
        .where(
            QuotaBucket.tenant_id == tenant_id,
            QuotaBucket.period_id == period_id,
            QuotaBucket.metric == metric,
            QuotaBucket.used <= QuotaBucket.hard_limit - quantity,
        )
        .values(used=QuotaBucket.used + quantity)
        .returning(QuotaBucket.used, QuotaBucket.hard_limit)
    )
    row = result.one_or_none()
    return (row.used, row.hard_limit) if row is not None else None
