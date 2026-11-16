# 用途：在本机读取指定账期的对账差异并输出 JSON。
import argparse
import asyncio
import json
from uuid import UUID

from app.core.config import Settings
from app.core.errors import DomainError
from app.db.session import create_db_engine, create_session_factory
from app.modules.billing.reconciliation import reconcile_period


async def run(period_id: UUID) -> int:
    engine = create_db_engine(Settings())
    try:
        factory = create_session_factory(engine)
        async with factory() as session, session.begin():
            report = await reconcile_period(session, period_id)
            print(json.dumps(report, ensure_ascii=False))
            return 0 if report["consistent"] else 1
    except DomainError as exc:
        print(json.dumps({"code": exc.code, "message": exc.message}, ensure_ascii=False))
        return 2
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="只读核对指定账期")
    parser.add_argument("period_id", type=UUID)
    raise SystemExit(asyncio.run(run(parser.parse_args().period_id)))


if __name__ == "__main__":
    main()
