# 用途：执行套餐查询并在同一事务中计量，重试读取事件中的原查询结果。
from hashlib import sha256
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.api_keys.context import ApiKeyContext
from app.modules.catalog.models import Plan
from app.modules.demo.schemas import DataQuery, DataQueryItem, DataQueryResult
from app.modules.metering.repository import get_usage_event
from app.modules.metering.schemas import UsageIn
from app.modules.metering.service import consume_usage, log_usage_result, usage_transaction
from app.modules.subscriptions.periods import utc_now


async def query_data(
    session: AsyncSession, context: ApiKeyContext, key: UUID, command: DataQuery
) -> DataQueryResult:
    event_id = uuid5(context.tenant_id, f"demo:data-query:{key}")
    digest = sha256(f"demo:data-query:{command.model_dump_json()}".encode()).hexdigest()
    usage_command = UsageIn(
        event_id=event_id, metric="data_query", quantity=1, occurred_at=utc_now()
    )
    async with usage_transaction(session):
        usage = await consume_usage(session, context, usage_command, payload_hash=digest)
        event = await get_usage_event(session, context.tenant_id, event_id)
        if event is None:
            raise RuntimeError("演示查询缺少用量记录")
        if usage.replayed:
            items = [DataQueryItem.model_validate(item) for item in event.result_snapshot["items"]]
        else:
            rows = await session.execute(
                select(Plan.code, Plan.name)
                .where(Plan.name.icontains(command.query, autoescape=True))
                .order_by(Plan.code)
                .limit(command.limit)
            )
            items = [DataQueryItem(code=row.code, name=row.name) for row in rows]
            event.result_snapshot = {
                **event.result_snapshot,
                "items": [item.model_dump() for item in items],
            }
        result = DataQueryResult(items=items, usage=usage)
    log_usage_result(result.usage)
    return result
