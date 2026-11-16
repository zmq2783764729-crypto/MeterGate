# 用途：在独立同步事务内处理账期事件、保存结算输入并记录耗尽重试的失败。
from datetime import UTC, datetime
from uuid import UUID

import dramatiq
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.modules.billing.events import PERIOD_CLOSED
from app.modules.billing.models import SettlementInput
from app.modules.metering.models import UsageEvent
from app.modules.subscriptions.models import BillingPeriod
from app.workers.broker import broker, settings
from app.workers.outbox_models import OutboxEvent

if settings.database_url is None:
    raise RuntimeError("后台任务需要配置 MG_DATABASE_URL")

worker_url = make_url(settings.database_url.get_secret_value()).set(drivername="postgresql+psycopg")
engine = create_engine(
    worker_url, pool_pre_ping=True, hide_parameters=True, connect_args={"connect_timeout": 5}
)
WorkerSession = sessionmaker(engine)


@dramatiq.actor(broker=broker, queue_name="billing", max_retries=10, min_backoff=1000)
def record_delivery_failure(message: dict, retry_data: dict) -> None:
    event_id = UUID(message["args"][0])
    with WorkerSession.begin() as session:
        session.execute(
            update(OutboxEvent)
            .where(
                OutboxEvent.id == event_id,
                ~select(SettlementInput.period_id)
                .where(SettlementInput.event_id == event_id)
                .exists(),
            )
            .values(
                failed_at=datetime.now(UTC),
                last_error=f"worker_retry_exhausted:{retry_data['retries']}",
            )
        )


@dramatiq.actor(
    broker=broker,
    queue_name="billing",
    max_retries=5,
    min_backoff=1000,
    max_backoff=60_000,
    on_retry_exhausted="record_delivery_failure",
)
def process_domain_event(event_id: str) -> None:
    with WorkerSession.begin() as session:
        event = session.get(OutboxEvent, UUID(event_id), with_for_update=True)
        if event is None:
            raise RuntimeError("领域事件不存在")
        if event.topic != PERIOD_CLOSED:
            raise RuntimeError("领域事件类型不受支持")
        if session.get(SettlementInput, event.aggregate_id) is not None:
            return
        period = session.get(BillingPeriod, event.aggregate_id)
        if (
            period is None
            or period.status != "closed"
            or event.payload != {"period_id": str(period.id), "tenant_id": str(period.tenant_id)}
        ):
            raise RuntimeError("结算事件与已关闭账期不匹配")
        total = session.scalar(
            select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
                UsageEvent.tenant_id == period.tenant_id, UsageEvent.period_id == period.id
            )
        )
        session.execute(
            insert(SettlementInput)
            .values(period_id=period.id, event_id=event.id, total_quantity=int(total))
            .on_conflict_do_nothing(index_elements=[SettlementInput.period_id])
        )
        event.failed_at = None
        event.last_error = None
