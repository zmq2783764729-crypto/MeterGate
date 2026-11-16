# 用途：预览或重新投递可确定的失败结算任务，并与审计一起提交。
import argparse
import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.config import Settings
from app.db.session import create_db_engine, create_session_factory
from app.modules.audit.service import record_audit
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.billing.events import PERIOD_CLOSED
from app.modules.billing.models import Invoice
from app.modules.subscriptions.models import BillingPeriod
from app.modules.tenants import models as tenant_models  # noqa: F401
from app.workers.outbox_models import OutboxEvent


async def run(apply: bool, limit: int, event_id: UUID | None) -> None:
    engine = create_db_engine(Settings())
    try:
        factory = create_session_factory(engine)
        async with factory() as session, session.begin():
            statement = (
                select(OutboxEvent, BillingPeriod.tenant_id)
                .join(BillingPeriod, BillingPeriod.id == OutboxEvent.aggregate_id)
                .where(
                    OutboxEvent.failed_at.is_not(None),
                    OutboxEvent.topic == PERIOD_CLOSED,
                    BillingPeriod.status == "closed",
                    ~select(Invoice.id).where(Invoice.period_id == BillingPeriod.id).exists(),
                )
                .order_by(OutboxEvent.failed_at, OutboxEvent.id)
                .limit(limit)
            )
            if event_id is not None:
                statement = statement.where(OutboxEvent.id == event_id)
            if apply:
                statement = statement.with_for_update(of=OutboxEvent, skip_locked=True)
            rows = (await session.execute(statement)).all()
            for event, tenant_id in rows:
                if apply:
                    event.attempts = 0
                    event.published_at = event.failed_at = event.last_error = None
                    event.next_attempt_at = datetime.now(UTC)
                    record_audit(session, tenant_id, "outbox.retry_requested", event.id)
        print(json.dumps({"applied": apply, "event_ids": [str(event.id) for event, _ in rows]}))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="重新投递失败结算任务，默认预览")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--event-id", type=UUID)
    args = parser.parse_args()
    if not 1 <= args.limit <= 500:
        parser.error("批大小必须在 1 到 500 之间")
    asyncio.run(run(args.apply, args.limit, args.event_id))


if __name__ == "__main__":
    main()
