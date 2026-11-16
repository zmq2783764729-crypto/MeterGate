# 用途：按用户或可信租户上下文访问企业成员数据，并提供管理操作的企业行锁与管理员计数。
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.tenants.context import TenantContext
from app.modules.tenants.models import MemberRole, Tenant, TenantMembership


async def add_tenant(session: AsyncSession, *, name: str) -> Tenant:
    tenant = Tenant(name=name)
    session.add(tenant)
    await session.flush()
    return tenant


async def add_membership(
    session: AsyncSession, *, tenant_id: UUID, user_id: UUID, role: MemberRole
) -> TenantMembership:
    membership = TenantMembership(tenant_id=tenant_id, user_id=user_id, role=role.value)
    session.add(membership)
    await session.flush()
    return membership


async def list_for_user(
    session: AsyncSession, *, user_id: UUID, limit: int, cursor: UUID | None
) -> list[tuple[Tenant, str]]:
    # user_id 只能来自登录身份；先限制成员关系，再分页，不能信任客户端传入的用户编号。
    statement = (
        select(Tenant, TenantMembership.role)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .where(TenantMembership.user_id == user_id)
        .order_by(Tenant.id)
        .limit(limit)
    )
    if cursor is not None:
        statement = statement.where(Tenant.id > cursor)
    rows = await session.execute(statement)
    return [(tenant, role) for tenant, role in rows]


async def get_membership(
    session: AsyncSession, *, tenant_id: UUID, user_id: UUID
) -> TenantMembership | None:
    return await session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user_id
        )
    )


async def lock_tenant(session: AsyncSession, context: TenantContext) -> Tenant | None:
    return await session.scalar(
        select(Tenant).where(Tenant.id == context.tenant_id).with_for_update()
    )


async def count_admins(session: AsyncSession, context: TenantContext) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(TenantMembership)
        .where(
            TenantMembership.tenant_id == context.tenant_id,
            TenantMembership.role == MemberRole.ADMIN.value,
        )
    )


async def list_members(
    session: AsyncSession, context: TenantContext, *, limit: int, cursor: UUID | None
) -> list[tuple[TenantMembership, str]]:
    statement = (
        select(TenantMembership, User.email)
        .join(User, TenantMembership.user_id == User.id)
        .where(TenantMembership.tenant_id == context.tenant_id)
        .order_by(TenantMembership.id)
        .limit(limit)
    )
    if cursor is not None:
        statement = statement.where(TenantMembership.id > cursor)
    rows = await session.execute(statement)
    return [(membership, email) for membership, email in rows]
