# 用途：查询公开套餐及历史版本，锁定套餐分配版本号，写入价格版本但不提交事务。
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Plan, PlanVersion
from app.modules.catalog.schemas import PlanVersionCreate


async def ensure_plan(session: AsyncSession, *, code: str, name: str) -> Plan:
    await session.execute(
        insert(Plan).values(code=code, name=name).on_conflict_do_nothing(index_elements=["code"])
    )
    return await session.scalar(select(Plan).where(Plan.code == code).with_for_update())


async def lock_plan(session: AsyncSession, plan_id: UUID) -> Plan | None:
    return await session.scalar(select(Plan).where(Plan.id == plan_id).with_for_update())


async def latest_number(session: AsyncSession, plan_id: UUID) -> int:
    return await session.scalar(
        select(func.coalesce(func.max(PlanVersion.version), 0)).where(
            PlanVersion.plan_id == plan_id
        )
    )


async def add_version(
    session: AsyncSession, *, plan_id: UUID, number: int, data: PlanVersionCreate
) -> PlanVersion:
    version = PlanVersion(plan_id=plan_id, version=number, **data.model_dump())
    session.add(version)
    await session.flush()
    return version


async def list_plans(session: AsyncSession, *, limit: int, cursor: UUID | None):
    latest = (
        select(PlanVersion.plan_id, func.max(PlanVersion.version).label("number"))
        .group_by(PlanVersion.plan_id)
        .subquery()
    )
    query = (
        select(Plan, PlanVersion)
        .join(latest, latest.c.plan_id == Plan.id)
        .join(
            PlanVersion, (PlanVersion.plan_id == Plan.id) & (PlanVersion.version == latest.c.number)
        )
        .order_by(Plan.id)
        .limit(limit)
    )
    if cursor is not None:
        query = query.where(Plan.id > cursor)
    return (await session.execute(query)).all()


async def list_versions(session: AsyncSession, *, plan_id: UUID, limit: int, cursor: int | None):
    query = (
        select(PlanVersion)
        .where(PlanVersion.plan_id == plan_id)
        .order_by(PlanVersion.version)
        .limit(limit)
    )
    if cursor is not None:
        query = query.where(PlanVersion.version > cursor)
    return list(await session.scalars(query))
