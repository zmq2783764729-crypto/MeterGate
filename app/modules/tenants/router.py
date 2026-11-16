# 用途：为main.py企业与成员接口提供处理函数、租户和角色依赖以及独立业务会话。
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_role
from app.dependencies.tenant import resolve_membership
from app.modules.auth.models import User
from app.modules.tenants.context import TenantContext
from app.modules.tenants.models import MemberRole
from app.modules.tenants.schemas import (
    MemberAddRequest,
    MemberPage,
    MemberPublic,
    MemberRoleRequest,
    TenantCreateRequest,
    TenantPage,
    TenantPublic,
)
from app.modules.tenants.service import (
    add_tenant_member,
    change_member_role,
    create_tenant_with_owner,
    list_my_tenants,
    list_tenant_members,
    remove_tenant_member,
)

CurrentUserDependency = Annotated[User, Depends(get_current_user)]
# 认证查询有自己的会话；业务会话不复用该依赖缓存，保证 begin 从干净事务开始。
TenantSessionDependency = Annotated[AsyncSession, Depends(get_session, use_cache=False)]
TenantContextDependency = Annotated[TenantContext, Depends(resolve_membership)]
AdminTenantDependency = Annotated[TenantContext, Depends(require_role(MemberRole.ADMIN))]


async def create_tenant(
    data: TenantCreateRequest, user: CurrentUserDependency, session: TenantSessionDependency
) -> TenantPublic:
    return await create_tenant_with_owner(session, user_id=user.id, data=data)


async def list_tenants(
    user: CurrentUserDependency,
    session: TenantSessionDependency,
    limit: int,
    cursor: UUID | None,
) -> TenantPage:
    return await list_my_tenants(session, user_id=user.id, limit=limit, cursor=cursor)


async def add_member(
    data: MemberAddRequest, context: AdminTenantDependency, session: TenantSessionDependency
) -> MemberPublic:
    return await add_tenant_member(session, context, data)


async def list_members(
    context: TenantContextDependency,
    session: TenantSessionDependency,
    limit: int,
    cursor: UUID | None,
) -> MemberPage:
    return await list_tenant_members(session, context, limit=limit, cursor=cursor)


async def update_member(
    user_id: UUID,
    data: MemberRoleRequest,
    context: AdminTenantDependency,
    session: TenantSessionDependency,
) -> MemberPublic:
    return await change_member_role(session, context, user_id=user_id, data=data)


async def delete_member(
    user_id: UUID, context: AdminTenantDependency, session: TenantSessionDependency
) -> None:
    await remove_tenant_member(session, context, user_id=user_id)
