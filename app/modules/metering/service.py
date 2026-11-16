# 用途：在同一事务内扣减额度并保存用量事件，按原结果快照处理重试。
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.api_keys.context import ApiKeyContext
from app.modules.metering import repository
from app.modules.metering.models import QuotaBucket, UsageEvent
from app.modules.metering.schemas import UsageIn, UsageResult, canonical_payload_hash
from app.modules.subscriptions.periods import utc_now
from app.modules.subscriptions.service import require_consumable_period


def _replay(event: UsageEvent, payload_hash: str) -> UsageResult:
    if event.payload_hash != payload_hash:
        raise DomainError("USAGE_EVENT_CONFLICT", "该事件编号已用于不同的用量请求", 409)
    result = UsageResult.model_validate(event.result_snapshot)
    return result.model_copy(update={"replayed": True})


async def ingest_usage(
    session: AsyncSession, context: ApiKeyContext, command: UsageIn
) -> UsageResult:
    async with session.begin():
        return await consume_usage(session, context, command)


async def consume_usage(
    session: AsyncSession,
    context: ApiKeyContext,
    command: UsageIn,
    *,
    payload_hash: str | None = None,
) -> UsageResult:
    if not session.in_transaction():
        raise RuntimeError("用量消费需要调用方事务")
    received_at = utc_now()
    tenant_id = context.tenant_id
    payload_hash = payload_hash if payload_hash is not None else canonical_payload_hash(command)
    event = await repository.get_usage_event(session, tenant_id, command.event_id)
    if event is not None:
        return _replay(event, payload_hash)

    try:
        period = await require_consumable_period(session, context, at=received_at)
    except DomainError as exc:
        if exc.code != "SUBSCRIPTION_NOT_CONSUMABLE":
            raise
        # 等锁期间可能已有同编号事件提交，同时账期进入不可消费状态。
        event = await repository.get_usage_event(session, tenant_id, command.event_id)
        if event is not None:
            return _replay(event, payload_hash)
        raise

    # 拿到订阅锁后重新读取，避免并发重试进入扣量流程。
    event = await repository.get_usage_event(session, tenant_id, command.event_id)
    if event is not None:
        return _replay(event, payload_hash)

    try:
        async with session.begin_nested():
            balance = await repository.debit_quota(
                session, tenant_id, period.id, command.metric, command.quantity
            )
            if balance is None:
                if await session.get(QuotaBucket, (tenant_id, period.id, command.metric)) is None:
                    raise DomainError("QUOTA_BUCKET_MISSING", "当前账期的用量额度未初始化", 500)
                raise DomainError("QUOTA_EXCEEDED", "本期剩余额度不足", 409)

            used, hard_limit = balance
            result = UsageResult(
                event_id=command.event_id,
                period_id=period.id,
                metric=command.metric,
                quantity=command.quantity,
                used=used,
                remaining=hard_limit - used,
            )
            session.add(
                UsageEvent(
                    tenant_id=tenant_id,
                    event_id=command.event_id,
                    period_id=period.id,
                    metric=command.metric,
                    quantity=command.quantity,
                    occurred_at=command.occurred_at,
                    received_at=received_at,
                    payload_hash=payload_hash,
                    result_snapshot=result.model_dump(mode="json", exclude={"replayed"}),
                )
            )
            await session.flush()
    except IntegrityError as exc:
        original = getattr(exc.orig, "__cause__", None)
        if getattr(original, "constraint_name", None) != "uq_usage_events_tenant_event":
            raise
        # SAVEPOINT 已回滚本次额度更新，外层事务可以读取获胜事件。
        event = await repository.get_usage_event(session, tenant_id, command.event_id)
        if event is None:
            raise
        return _replay(event, payload_hash)

    return result
