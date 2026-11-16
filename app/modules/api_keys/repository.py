# 用途：按可信租户上下文写入、分页和查找密钥，机器认证仅按公开编号定位摘要记录。
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.api_keys.models import ApiKey
from app.modules.tenants.context import TenantContext


async def add_key(session: AsyncSession, key: ApiKey) -> ApiKey:
    session.add(key)
    await session.flush()
    return key


async def list_keys(
    session: AsyncSession, context: TenantContext, *, limit: int, cursor: UUID | None
) -> list[ApiKey]:
    statement = (
        select(ApiKey).where(ApiKey.tenant_id == context.tenant_id).order_by(ApiKey.id).limit(limit)
    )
    if cursor is not None:
        statement = statement.where(ApiKey.id > cursor)
    return list(await session.scalars(statement))


async def get_tenant_key(
    session: AsyncSession, context: TenantContext, key_id: UUID
) -> ApiKey | None:
    return await session.scalar(
        select(ApiKey).where(ApiKey.tenant_id == context.tenant_id, ApiKey.id == key_id)
    )


async def get_auth_key(session: AsyncSession, key_id: UUID) -> ApiKey | None:
    return await session.get(ApiKey, key_id)
