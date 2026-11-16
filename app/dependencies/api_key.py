# 用途：验证X-API-Key摘要、撤销和有效期，并通过可复用依赖限定机器调用scope。
import hmac
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.db.session import get_session
from app.modules.api_keys.context import ApiKeyContext
from app.modules.api_keys.models import ApiKeyScope
from app.modules.api_keys.repository import get_auth_key
from app.modules.api_keys.security import ApiKeyMaterial, invalid_api_key, parse_api_key

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="企业程序访问密钥")


def get_api_key_material(
    raw_key: Annotated[str | None, Security(api_key_header)],
) -> ApiKeyMaterial:
    return parse_api_key(raw_key)


async def authenticate_api_key(
    material: Annotated[ApiKeyMaterial, Depends(get_api_key_material)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiKeyContext:
    key = await get_auth_key(session, material.key_id)
    if key is None or not hmac.compare_digest(key.token_digest, material.token_digest):
        raise invalid_api_key()
    if key.revoked_at is not None or (
        key.expires_at is not None and key.expires_at <= datetime.now(UTC)
    ):
        raise invalid_api_key()
    return ApiKeyContext(
        key_id=key.id,
        tenant_id=key.tenant_id,
        scopes=frozenset(ApiKeyScope(scope) for scope in key.scopes),
    )


def require_api_key_scope(scope: ApiKeyScope) -> Callable[..., ApiKeyContext]:
    def check_scope(
        context: Annotated[ApiKeyContext, Depends(authenticate_api_key)],
    ) -> ApiKeyContext:
        if scope not in context.scopes:
            raise DomainError("INSUFFICIENT_SCOPE", "API Key缺少所需权限", 403)
        return context

    return check_scope
