# 用途：幂等初始化基础与专业套餐，或通过平台本机命令追加新价格版本，拒绝非法金额和额度。
import argparse
import asyncio
import json

from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings
from app.core.errors import DomainError
from app.db.session import create_db_engine, create_session_factory
from app.modules.catalog.models import Plan
from app.modules.catalog.schemas import PlanVersionCreate
from app.modules.catalog.service import create_plan_version, seed_catalog


async def execute(args: argparse.Namespace) -> list[dict]:
    # 在连接数据库之前校验输入；StrictInt不会把浮点金额转为整数。
    data = None
    if args.command == "create-version":
        data = PlanVersionCreate(
            base_fee_cents=args.base_fee_cents,
            unit_price_cents=args.unit_price_cents,
            hard_limit=args.hard_limit,
        )
    engine = create_db_engine(Settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            if data is None:
                return [row.model_dump(mode="json") for row in await seed_catalog(session)]
            # 查询用独立会话；发布会话从干净事务开始。
            plan_id = await session.scalar(select(Plan.id).where(Plan.code == args.code))
        if plan_id is None:
            raise DomainError("PLAN_NOT_FOUND", "套餐不存在，请先初始化或检查code", 404)
        async with factory() as session:
            return [
                (await create_plan_version(session, plan_id=plan_id, data=data)).model_dump(
                    mode="json"
                )
            ]
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="平台套餐维护：金额单位为整数分")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("seed", help="仅初始化缺失演示套餐，不覆盖既有版本")
    publish = commands.add_parser("create-version", help="按套餐code追加新价格版本")
    publish.add_argument("--code", required=True)
    publish.add_argument("--base-fee-cents", type=int, required=True)
    publish.add_argument("--unit-price-cents", type=int, required=True)
    publish.add_argument("--hard-limit", type=int, required=True)
    args = parser.parse_args()
    try:
        rows = asyncio.run(execute(args))
    except (ValidationError, DomainError) as exc:
        message = (
            "参数无效：金额必须为非负整数分，额度必须为正整数且在范围内"
            if isinstance(exc, ValidationError)
            else exc.message
        )
        parser.exit(2, message + "\n")
    print(json.dumps({"versions_created": len(rows), "items": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
