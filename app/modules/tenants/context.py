# 用途：提供不可变租户上下文，携带经过数据库成员关系验证的企业、用户和角色。
from dataclasses import dataclass
from uuid import UUID

from app.modules.tenants.models import MemberRole


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    user_id: UUID
    role: MemberRole
