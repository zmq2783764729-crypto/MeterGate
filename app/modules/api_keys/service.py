# 用途：在管理员授权事务内创建或撤销企业密钥，列表只输出安全元数据。
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.api_keys import repository
from app.modules.api_keys.models import ApiKey
from app.modules.api_keys.schemas import (
    ApiKeyCreated,
    ApiKeyCreateRequest,
    ApiKeyPage,
    ApiKeyPublic,
)
from app.modules.api_keys.security import generate_api_key
from app.modules.tenants.authorization import lock_and_authorize_admin
from app.modules.tenants.context import TenantContext


async def create_api_key(
    session: AsyncSession, context: TenantContext, data: ApiKeyCreateRequest
) -> ApiKeyCreated:
    generated = generate_api_key()
    async with session.begin():
        await lock_and_authorize_admin(session, context)
        # 依赖校验之后仍可能等待锁，写入前再确认期限，避免存入已经过期的新密钥。
        if data.expires_at is not None and data.expires_at <= datetime.now(UTC):
            raise DomainError("INVALID_EXPIRY", "到期时间必须晚于当前时间", 422)
        key = await repository.add_key(
            session,
            ApiKey(
                id=generated.key_id,
                tenant_id=context.tenant_id,
                created_by=context.user_id,
                name=data.name,
                prefix=generated.prefix,
                token_digest=generated.token_digest,
                scopes=[scope.value for scope in data.scopes],
                expires_at=data.expires_at,
            ),
        )
        result = ApiKeyCreated(
            **ApiKeyPublic.model_validate(key).model_dump(),
            api_key=generated.token.get_secret_value(),
        )
    return result


async def list_api_keys(
    session: AsyncSession, context: TenantContext, *, limit: int, cursor: UUID | None
) -> ApiKeyPage:
    rows = await repository.list_keys(session, context, limit=limit + 1, cursor=cursor)
    return ApiKeyPage(
        items=[ApiKeyPublic.model_validate(key) for key in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


async def revoke_api_key(session: AsyncSession, context: TenantContext, key_id: UUID) -> None:
    async with session.begin():
        await lock_and_authorize_admin(session, context)
        key = await repository.get_tenant_key(session, context, key_id)
        if key is None:
            raise DomainError("API_KEY_NOT_FOUND", "该企业中不存在此API Key", 404)
        if key.revoked_at is None:
            key.revoked_at = datetime.now(UTC)
            await session.flush()
