# 用途：为main.py公开套餐只读接口提供会话依赖和处理函数，不提供租户管理员发布接口。
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.catalog import service
from app.modules.catalog.schemas import PlanPage, PlanVersionPage, PlanVersionPublic

CatalogSession = Annotated[AsyncSession, Depends(get_session)]


async def list_plans(session: CatalogSession, limit: int, cursor: UUID | None) -> PlanPage:
    return await service.get_plans(session, limit=limit, cursor=cursor)


async def list_versions(
    plan_id: UUID, session: CatalogSession, limit: int, cursor: int | None
) -> PlanVersionPage:
    return await service.get_plan_versions(session, plan_id=plan_id, limit=limit, cursor=cursor)


async def version_detail(version_id: UUID, session: CatalogSession) -> PlanVersionPublic:
    return await service.get_version(session, version_id)
