# 用途：提供可复用角色依赖，在可信租户上下文基础上限制接口允许的成员角色。
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from app.core.errors import DomainError
from app.dependencies.tenant import resolve_membership
from app.modules.tenants.context import TenantContext
from app.modules.tenants.models import MemberRole


def require_role(*roles: MemberRole) -> Callable[..., TenantContext]:
    allowed = frozenset(roles)

    def check_role(
        context: Annotated[TenantContext, Depends(resolve_membership)],
    ) -> TenantContext:
        if context.role not in allowed:
            raise DomainError("FORBIDDEN", "没有权限执行此操作", 403)
        return context

    return check_role
