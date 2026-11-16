# 用途：将URL企业编号与已认证用户的数据库成员关系匹配，生成可信租户上下文。
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.modules.auth.models import User
from app.modules.tenants.context import TenantContext
from app.modules.tenants.models import MemberRole
from app.modules.tenants.repository import get_membership


async def resolve_membership(
    tenant_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantContext:
    membership = await get_membership(session, tenant_id=tenant_id, user_id=user.id)
    if membership is None:
        # 未加入与企业不存在返回相同结果，不通过编号猜测暴露企业信息。
        raise DomainError("TENANT_NOT_FOUND", "企业不存在或你未加入该企业", 404)
    return TenantContext(tenant_id=tenant_id, user_id=user.id, role=MemberRole(membership.role))
