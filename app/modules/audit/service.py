# 用途：在业务事务中记录审计，并按企业与时间分页读取。
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.middleware.request_context import get_request_id
from app.modules.audit.models import AuditEntry
from app.modules.tenants.context import TenantContext


class AuditPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    resource_id: UUID
    request_id: str | None
    details: dict[str, str]
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditPublic]
    next_cursor: UUID | None = None


def record_audit(
    session: AsyncSession,
    tenant_id: UUID,
    action: str,
    resource_id: UUID,
    *,
    actor_user_id: UUID | None = None,
    details: dict[str, str] | None = None,
) -> None:
    if not session.in_transaction():
        raise RuntimeError("审计必须在业务事务内写入")
    session.add(
        AuditEntry(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_id=resource_id,
            request_id=get_request_id(),
            details=details or {},
        )
    )


async def list_audit(
    session: AsyncSession, context: TenantContext, limit: int, cursor: UUID | None
) -> AuditPage:
    statement = select(AuditEntry).where(AuditEntry.tenant_id == context.tenant_id)
    if cursor is not None:
        anchor = await session.scalar(statement.where(AuditEntry.id == cursor))
        if anchor is None:
            raise DomainError("INVALID_AUDIT_CURSOR", "审计游标无效", 422)
        statement = statement.where(
            tuple_(AuditEntry.created_at, AuditEntry.id) < (anchor.created_at, anchor.id)
        )
    rows = (
        await session.scalars(
            statement.order_by(AuditEntry.created_at.desc(), AuditEntry.id.desc()).limit(limit + 1)
        )
    ).all()
    return AuditPage(
        items=[AuditPublic.model_validate(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )
