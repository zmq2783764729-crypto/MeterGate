# 用途：为main.py提供API Key管理处理函数及两种scope的机器身份校验依赖。
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Response

from app.dependencies.api_key import require_api_key_scope
from app.modules.api_keys.context import ApiKeyContext
from app.modules.api_keys.models import ApiKeyScope
from app.modules.api_keys.schemas import (
    ApiKeyCreated,
    ApiKeyCreateRequest,
    ApiKeyIdentity,
    ApiKeyPage,
)
from app.modules.api_keys.service import create_api_key, list_api_keys, revoke_api_key
from app.modules.tenants.router import AdminTenantDependency, TenantSessionDependency

DemoReadKeyDependency = Annotated[
    ApiKeyContext, Depends(require_api_key_scope(ApiKeyScope.DEMO_READ))
]
UsageWriteKeyDependency = Annotated[
    ApiKeyContext, Depends(require_api_key_scope(ApiKeyScope.USAGE_WRITE))
]


async def create_key(
    data: ApiKeyCreateRequest,
    response: Response,
    context: AdminTenantDependency,
    session: TenantSessionDependency,
) -> ApiKeyCreated:
    result = await create_api_key(session, context, data)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return result


async def list_keys(
    context: AdminTenantDependency,
    session: TenantSessionDependency,
    limit: int,
    cursor: UUID | None,
) -> ApiKeyPage:
    return await list_api_keys(session, context, limit=limit, cursor=cursor)


async def revoke_key(
    key_id: UUID, context: AdminTenantDependency, session: TenantSessionDependency
) -> None:
    await revoke_api_key(session, context, key_id)


def key_identity(context: ApiKeyContext) -> ApiKeyIdentity:
    return ApiKeyIdentity(
        key_id=context.key_id, tenant_id=context.tenant_id, scopes=sorted(context.scopes)
    )
