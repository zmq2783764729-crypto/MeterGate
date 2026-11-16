# 用途：以追加方式发布价格版本，幂等初始化演示套餐，并组装公开套餐与历史版本查询。
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.catalog import repository
from app.modules.catalog.models import Plan, PlanVersion
from app.modules.catalog.schemas import (
    PlanPage,
    PlanPublic,
    PlanVersionCreate,
    PlanVersionPage,
    PlanVersionPublic,
)

DEMO_PLANS = (
    (
        "basic",
        "基础套餐",
        PlanVersionCreate(base_fee_cents=4900, unit_price_cents=2, hard_limit=10000),
    ),
    (
        "professional",
        "专业套餐",
        PlanVersionCreate(base_fee_cents=19900, unit_price_cents=1, hard_limit=100000),
    ),
)


async def seed_catalog(session: AsyncSession) -> list[PlanVersionPublic]:
    results = []
    async with session.begin():
        for code, name, data in DEMO_PLANS:
            plan = await repository.ensure_plan(session, code=code, name=name)
            if await repository.latest_number(session, plan.id) == 0:
                row = await repository.add_version(session, plan_id=plan.id, number=1, data=data)
                results.append(PlanVersionPublic.model_validate(row))
    return results


async def create_plan_version(
    session: AsyncSession, *, plan_id: UUID, data: PlanVersionCreate
) -> PlanVersionPublic:
    async with session.begin():
        if await repository.lock_plan(session, plan_id) is None:
            raise DomainError("PLAN_NOT_FOUND", "套餐不存在", 404)
        number = await repository.latest_number(session, plan_id) + 1
        row = await repository.add_version(session, plan_id=plan_id, number=number, data=data)
        result = PlanVersionPublic.model_validate(row)
    return result


async def get_plans(session: AsyncSession, *, limit: int, cursor: UUID | None) -> PlanPage:
    rows = await repository.list_plans(session, limit=limit + 1, cursor=cursor)
    return PlanPage(
        items=[
            PlanPublic(
                id=p.id,
                code=p.code,
                name=p.name,
                latest_version=PlanVersionPublic.model_validate(v),
            )
            for p, v in rows[:limit]
        ],
        next_cursor=rows[limit - 1][0].id if len(rows) > limit else None,
    )


async def get_plan_versions(
    session: AsyncSession, *, plan_id: UUID, limit: int, cursor: int | None
) -> PlanVersionPage:
    if await session.get(Plan, plan_id) is None:
        raise DomainError("PLAN_NOT_FOUND", "套餐不存在", 404)
    rows = await repository.list_versions(session, plan_id=plan_id, limit=limit + 1, cursor=cursor)
    return PlanVersionPage(
        items=[PlanVersionPublic.model_validate(v) for v in rows[:limit]],
        next_cursor=rows[limit - 1].version if len(rows) > limit else None,
    )


async def get_version(session: AsyncSession, version_id: UUID) -> PlanVersionPublic:
    version = await session.get(PlanVersion, version_id)
    if version is None:
        raise DomainError("PLAN_VERSION_NOT_FOUND", "套餐价格版本不存在", 404)
    return PlanVersionPublic.model_validate(version)
