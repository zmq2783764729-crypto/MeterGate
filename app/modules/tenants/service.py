# 用途：编排企业与成员管理事务，复核管理员权限并通过企业行锁保护最后一位管理员。
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.auth import repository as user_repository
from app.modules.tenants import repository
from app.modules.tenants.authorization import lock_and_authorize_admin
from app.modules.tenants.context import TenantContext
from app.modules.tenants.models import MemberRole, Tenant, TenantMembership
from app.modules.tenants.schemas import (
    MemberAddRequest,
    MemberPage,
    MemberPublic,
    MemberRoleRequest,
    TenantCreateRequest,
    TenantPage,
    TenantPublic,
)


def to_public(tenant: Tenant, role: str) -> TenantPublic:
    return TenantPublic(
        id=tenant.id, name=tenant.name, role=MemberRole(role), created_at=tenant.created_at
    )


async def create_tenant_with_owner(
    session: AsyncSession, *, user_id: UUID, data: TenantCreateRequest
) -> TenantPublic:
    # 本服务使用独立写会话；不能与已因认证 SELECT 而自动开启事务的会话混用。
    async with session.begin():
        tenant = await repository.add_tenant(session, name=data.name)
        await repository.add_membership(
            session, tenant_id=tenant.id, user_id=user_id, role=MemberRole.ADMIN
        )
        result = to_public(tenant, MemberRole.ADMIN)
    return result


async def list_my_tenants(
    session: AsyncSession, *, user_id: UUID, limit: int, cursor: UUID | None
) -> TenantPage:
    # 多取一条判断是否还有下一页；顺序为 UUID 升序，不表示创建时间顺序。
    rows = await repository.list_for_user(session, user_id=user_id, limit=limit + 1, cursor=cursor)
    visible = rows[:limit]
    return TenantPage(
        items=[to_public(tenant, role) for tenant, role in visible],
        next_cursor=visible[-1][0].id if len(rows) > limit else None,
    )


def member_public(membership: TenantMembership, email: str) -> MemberPublic:
    return MemberPublic(
        id=membership.id,
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        email=email,
        role=MemberRole(membership.role),
        created_at=membership.created_at,
    )


async def _target_member(
    session: AsyncSession, context: TenantContext, user_id: UUID
) -> TenantMembership:
    target = await repository.get_membership(session, tenant_id=context.tenant_id, user_id=user_id)
    if target is None:
        raise DomainError("MEMBER_NOT_FOUND", "该企业中不存在此成员", 404)
    return target


async def _protect_last_admin(
    session: AsyncSession, context: TenantContext, target: TenantMembership
) -> None:
    if target.role == MemberRole.ADMIN and await repository.count_admins(session, context) <= 1:
        raise DomainError("LAST_ADMIN_REQUIRED", "企业必须至少保留一名管理员", 409)


async def add_tenant_member(
    session: AsyncSession, context: TenantContext, data: MemberAddRequest
) -> MemberPublic:
    try:
        async with session.begin():
            await lock_and_authorize_admin(session, context)
            user = await user_repository.get_user_by_email(session, str(data.email))
            if user is None:
                raise DomainError("USER_NOT_FOUND", "该邮箱尚未注册", 404)
            if (
                await repository.get_membership(
                    session, tenant_id=context.tenant_id, user_id=user.id
                )
                is not None
            ):
                raise DomainError("MEMBER_ALREADY_EXISTS", "该用户已加入此企业", 409)
            member = await repository.add_membership(
                session, tenant_id=context.tenant_id, user_id=user.id, role=data.role
            )
            result = member_public(member, user.email)
        return result
    except IntegrityError as exc:
        driver_error = getattr(exc.orig, "__cause__", None)
        if getattr(driver_error, "constraint_name", None) == "uq_tenant_memberships_tenant_user":
            raise DomainError("MEMBER_ALREADY_EXISTS", "该用户已加入此企业", 409) from exc
        raise


async def list_tenant_members(
    session: AsyncSession, context: TenantContext, *, limit: int, cursor: UUID | None
) -> MemberPage:
    rows = await repository.list_members(session, context, limit=limit + 1, cursor=cursor)
    visible = rows[:limit]
    return MemberPage(
        items=[member_public(member, email) for member, email in visible],
        next_cursor=visible[-1][0].id if len(rows) > limit else None,
    )


async def change_member_role(
    session: AsyncSession, context: TenantContext, *, user_id: UUID, data: MemberRoleRequest
) -> MemberPublic:
    async with session.begin():
        await lock_and_authorize_admin(session, context)
        target = await _target_member(session, context, user_id)
        if target.role == MemberRole.ADMIN and data.role != MemberRole.ADMIN:
            await _protect_last_admin(session, context, target)
        target.role = data.role.value
        await session.flush()
        user = await user_repository.get_user_by_id(session, user_id)
        result = member_public(target, user.email)
    return result


async def remove_tenant_member(
    session: AsyncSession, context: TenantContext, *, user_id: UUID
) -> None:
    async with session.begin():
        await lock_and_authorize_admin(session, context)
        target = await _target_member(session, context, user_id)
        await _protect_last_admin(session, context, target)
        await session.delete(target)
        await session.flush()
