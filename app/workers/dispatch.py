# 用途：在独立进程中轮询事务 Outbox 并把事件编号发送至 Redis 队列。
import asyncio
import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import create_db_engine, create_session_factory
from app.workers.outbox import publish_batch
from app.workers.tasks import process_domain_event, settings

logger = logging.getLogger(__name__)


async def publish(event_id: UUID) -> None:
    await asyncio.to_thread(process_domain_event.send, str(event_id))


async def run() -> None:
    engine = create_db_engine(settings)
    factory = create_session_factory(engine)
    try:
        while True:
            try:
                async with factory() as session:
                    count = await publish_batch(session, publish)
                if count == 0:
                    await asyncio.sleep(1)
            except SQLAlchemyError as exc:
                logger.error("Outbox 轮询失败 %s", type(exc).__name__)
                await asyncio.sleep(3)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
