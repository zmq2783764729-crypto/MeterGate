# 用途：按企业读取计量摘要、账期价格估算与带游标的用量明细。
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.metering.models import QuotaBucket, UsageEvent
from app.modules.metering.schemas import (
    UsageEventPage,
    UsageEventPublic,
    UsageListQuery,
    UsageMetric,
    UsageSummary,
)
from app.modules.subscriptions.models import BillingPeriod, PeriodTerms


async def usage_summary(
    session: AsyncSession, tenant_id: UUID, period_id: UUID | None, metric: UsageMetric
) -> UsageSummary:
    period_filter = BillingPeriod.id == period_id if period_id else BillingPeriod.status == "open"
    row = (
        await session.execute(
            select(QuotaBucket, PeriodTerms)
            .join(BillingPeriod, BillingPeriod.id == QuotaBucket.period_id)
            .join(PeriodTerms, PeriodTerms.period_id == BillingPeriod.id)
            .where(QuotaBucket.tenant_id == tenant_id, QuotaBucket.metric == metric, period_filter)
        )
    ).one_or_none()
    if row is None:
        raise DomainError("USAGE_PERIOD_NOT_FOUND", "未找到该企业的账期用量", 404)
    bucket, terms = row
    return UsageSummary(
        period_id=bucket.period_id,
        metric=metric,
        used=bucket.used,
        hard_limit=bucket.hard_limit,
        remaining=bucket.hard_limit - bucket.used,
        currency=terms.currency,
        estimated_total_cents=terms.base_fee_cents + terms.unit_price_cents * bucket.used,
    )


async def usage_events(
    session: AsyncSession, tenant_id: UUID, query: UsageListQuery
) -> UsageEventPage:
    if query.start and query.end and query.start >= query.end:
        raise DomainError("INVALID_USAGE_RANGE", "开始时间必须早于结束时间", 422)
    filters = [UsageEvent.tenant_id == tenant_id, UsageEvent.metric == query.metric]
    if query.period_id:
        filters.append(UsageEvent.period_id == query.period_id)
    if query.start:
        filters.append(UsageEvent.received_at >= query.start)
    if query.end:
        filters.append(UsageEvent.received_at < query.end)

    statement = select(UsageEvent).where(*filters)
    if query.cursor:
        anchor = await session.scalar(statement.where(UsageEvent.id == query.cursor))
        if anchor is None:
            raise DomainError("INVALID_USAGE_CURSOR", "用量游标无效", 422)
        statement = statement.where(
            tuple_(UsageEvent.received_at, UsageEvent.id) < (anchor.received_at, anchor.id)
        )
    rows = (
        await session.scalars(
            statement.order_by(UsageEvent.received_at.desc(), UsageEvent.id.desc()).limit(
                query.limit + 1
            )
        )
    ).all()
    return UsageEventPage(
        items=[UsageEventPublic.model_validate(row) for row in rows[: query.limit]],
        next_cursor=rows[query.limit - 1].id if len(rows) > query.limit else None,
    )
