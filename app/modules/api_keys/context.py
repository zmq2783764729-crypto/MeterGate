# 用途：提供通过API Key验证的机器身份，租户和权限仅来自数据库密钥记录。
from dataclasses import dataclass
from uuid import UUID

from app.modules.api_keys.models import ApiKeyScope


@dataclass(frozen=True)
class ApiKeyContext:
    key_id: UUID
    tenant_id: UUID
    scopes: frozenset[ApiKeyScope]
