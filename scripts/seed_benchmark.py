# 用途：在专用压测库的开放账期批量准备历史用量与匹配的额度余额。
import argparse
import asyncio
from datetime import timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.session import create_db_engine, create_session_factory
from app.modules.metering.models import QuotaBucket
from app.modules.subscriptions.models import BillingPeriod

SEED_EVENTS = text("""
    WITH events AS (
        SELECT gen_random_uuid() AS id,
               CAST(:at AS timestamptz) - make_interval(secs => (:count - n) * 0.000001) AS ts, n
        FROM generate_series(1, CAST(:count AS integer)) AS s(n)
    )
    INSERT INTO usage_events (
        id, tenant_id, event_id, period_id, metric, quantity, occurred_at, received_at,
        payload_hash, result_snapshot
    )
    SELECT id, CAST(:tenant_id AS uuid), id, CAST(:period_id AS uuid), 'data_query', 1, ts, ts,
           encode(sha256(convert_to(
             '{"event_id":"' || id::text || '","metric":"data_query","occurred_at":"' ||
             CASE WHEN date_part('microseconds', ts)::bigint % 1000000 = 0
                THEN to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
                ELSE to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
             END || '","quantity":1}', 'UTF8')), 'hex'),
           jsonb_build_object('event_id', id, 'period_id', CAST(:period_id AS uuid),
                              'metric', 'data_query', 'quantity', 1,
                              'used', CAST(:used AS bigint) + n,
                              'remaining', CAST(:remaining AS bigint) - n)
    FROM events
""")


async def run(period_id: UUID, count: int) -> None:
    settings = Settings()
    url = settings.database_url
    if (
        settings.environment == "production"
        or url is None
        or not (make_url(url.get_secret_value()).database or "").startswith("metergate_bench_")
    ):
        raise SystemExit("批量造数只允许专用 metergate_bench_ 数据库")
    engine = create_db_engine(settings)
    try:
        factory = create_session_factory(engine)
        async with factory() as session, session.begin():
            period = await session.get(BillingPeriod, period_id, with_for_update=True)
            if period is None or period.status != "open":
                raise SystemExit("请指定开放账期")
            bucket = await session.get(
                QuotaBucket, (period.tenant_id, period.id, "data_query"), with_for_update=True
            )
            if bucket is None or bucket.hard_limit - bucket.used < count:
                raise SystemExit("额度不足以写入本批数据")
            await session.execute(
                SEED_EVENTS,
                {
                    "tenant_id": period.tenant_id,
                    "period_id": period.id,
                    "count": count,
                    # 在账期开始后一秒造数，保留账期归属。
                    "at": period.period_start.replace(microsecond=0) + timedelta(seconds=2),
                    "used": bucket.used,
                    "remaining": bucket.hard_limit - bucket.used,
                },
            )
            bucket.used += count
        print(f"已写入 {count} 条用量事件")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="在压测数据库批量生成用量历史")
    parser.add_argument("period_id", type=UUID)
    parser.add_argument("--count", type=int, default=100_000)
    args = parser.parse_args()
    if not 1 <= args.count <= 1_000_000:
        parser.error("条数须在 1 到 1,000,000 之间")
    asyncio.run(run(args.period_id, args.count))


if __name__ == "__main__":
    main()
