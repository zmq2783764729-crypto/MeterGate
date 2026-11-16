# 用途：随业务事务写领域事件，批量领取并按退避时间重新发布失败事件。
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.outbox_models import OutboxEvent

MAX_ATTEMPTS = 10


async def enqueue_domain_event(
    session: AsyncSession, topic: str, aggregate_id: UUID, payload: dict[str, str]
) -> None:
    if not session.in_transaction():
        raise RuntimeError("领域事件需要与业务变更在同一事务内写入")
    await session.execute(
        insert(OutboxEvent)
        .values(topic=topic, aggregate_id=aggregate_id, payload=payload)
        .on_conflict_do_nothing(constraint="uq_outbox_topic_aggregate")
    )


async def publish_batch(
    session: AsyncSession, publisher: Callable[[UUID], Awaitable[None]], *, limit: int = 20
) -> int:
    async with session.begin():
        events = (
            await session.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.published_at.is_(None),
                    OutboxEvent.failed_at.is_(None),
                    OutboxEvent.next_attempt_at <= datetime.now(UTC),
                )
                .order_by(OutboxEvent.next_attempt_at, OutboxEvent.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for event in events:
            event.attempts += 1
            try:
                await publisher(event.id)
            except Exception as exc:
                now = datetime.now(UTC)
                event.last_error = type(exc).__name__[:100]
                if event.attempts >= MAX_ATTEMPTS:
                    event.failed_at = now
                else:
                    event.next_attempt_at = now + timedelta(seconds=min(2**event.attempts, 300))
            else:
                # 发布完成后若事务未提交，下一轮会再次发布，消费者按事件编号去重。
                event.published_at = datetime.now(UTC)
                event.last_error = None
        return len(events)
