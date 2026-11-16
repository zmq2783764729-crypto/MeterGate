# 用途：为企业管理写事务锁定企业行，并复核操作者当前数据库中的管理员身份。
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.tenants import repository
from app.modules.tenants.context import TenantContext
from app.modules.tenants.models import MemberRole


async def lock_and_authorize_admin(session: AsyncSession, context: TenantContext) -> None:
    if await repository.lock_tenant(session, context) is None:
        raise DomainError("TENANT_NOT_FOUND", "企业不存在或你未加入该企业", 404)
    actor = await repository.get_membership(
        session, tenant_id=context.tenant_id, user_id=context.user_id
    )
    if actor is None:
        raise DomainError("TENANT_NOT_FOUND", "企业不存在或你未加入该企业", 404)
    if actor.role != MemberRole.ADMIN:
        raise DomainError("FORBIDDEN", "没有权限执行此操作", 403)
