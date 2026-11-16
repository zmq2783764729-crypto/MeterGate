# 用途：扫描到期账期并复用 API 的订阅轮转事务，支持显式的本地演示时钟。
import argparse
import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.config import Settings
from app.db.session import create_db_engine, create_session_factory
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.subscriptions.models import BillingPeriod
from app.modules.subscriptions.period_service import resolve_open_period
from app.modules.subscriptions.periods import utc_now
from app.modules.tenants import models as tenant_models  # noqa: F401


async def run(settings: Settings, at: datetime, batch_size: int) -> None:
    engine = create_db_engine(settings)
    factory = create_session_factory(engine)
    cursor: UUID | None = None
    processed = 0
    try:
        while True:
            statement = select(BillingPeriod.tenant_id).where(
                BillingPeriod.status == "open", BillingPeriod.period_end <= at
            )
            if cursor is not None:
                statement = statement.where(BillingPeriod.tenant_id > cursor)
            async with factory() as session:
                tenants = (
                    await session.scalars(
                        statement.order_by(BillingPeriod.tenant_id).limit(batch_size)
                    )
                ).all()
            if not tenants:
                break
            for tenant_id in tenants:
                async with factory() as session, session.begin():
                    await resolve_open_period(session, tenant_id, at)
                processed += 1
            cursor = tenants[-1]
    finally:
        await engine.dispose()
    print(f"已处理 {processed} 个到期企业")


def main() -> None:
    parser = argparse.ArgumentParser(description="关闭到期账期并按订阅状态续期")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--at", help="显式演示时钟，仅用于非生产环境，需带时区")
    args = parser.parse_args()
    settings = Settings()
    if not 1 <= args.batch_size <= 1000:
        parser.error("批大小必须在 1 和 1000 之间")
    at = utc_now()
    if args.at:
        if settings.environment == "production":
            parser.error("生产环境使用真实时钟")
        try:
            at = datetime.fromisoformat(args.at)
            if at.utcoffset() is None:
                raise ValueError
            at = at.astimezone(UTC)
        except (ValueError, OverflowError):
            parser.error("--at 需要带时区的 ISO 8601 时间")
    asyncio.run(run(settings, at, args.batch_size))


if __name__ == "__main__":
    main()
