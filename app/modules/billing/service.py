# 用途：为关闭账期生成不可重复的账单，并按企业读取账单与明细。
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.billing.calculator import calculate_invoice
from app.modules.billing.models import Invoice, InvoiceItem
from app.modules.billing.schemas import InvoiceDetail, InvoiceLine, InvoicePage, InvoiceSummary
from app.modules.catalog import models as catalog_models  # noqa: F401
from app.modules.metering.models import UsageEvent
from app.modules.subscriptions.models import BillingPeriod, PeriodTerms


def generate_invoice(session: Session, period_id: UUID) -> Invoice:
    period = session.get(BillingPeriod, period_id, with_for_update=True)
    if period is None or period.status != "closed":
        raise ValueError("只有已关闭的账期可生成账单")
    existing = session.scalar(select(Invoice).where(Invoice.period_id == period_id))
    if existing is not None:
        return existing
    terms = session.get(PeriodTerms, period_id)
    if terms is None:
        raise RuntimeError("账期缺少计费条款快照")
    total = session.scalar(
        select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.tenant_id == period.tenant_id, UsageEvent.period_id == period.id
        )
    )
    draft = calculate_invoice(terms, int(total))
    invoice = Invoice(
        period_id=period_id,
        tenant_id=period.tenant_id,
        plan_version_id=terms.plan_version_id,
        currency=terms.currency,
        base_fee_cents=draft.base_fee_cents,
        usage_fee_cents=draft.usage_fee_cents,
        total_cents=draft.total_cents,
    )
    session.add(invoice)
    session.flush()
    session.add_all(InvoiceItem(invoice_id=invoice.id, **line.model_dump()) for line in draft.items)
    session.flush()
    return invoice


async def list_invoices(
    session: AsyncSession, tenant_id: UUID, limit: int, cursor: UUID | None
) -> InvoicePage:
    statement = select(Invoice).where(Invoice.tenant_id == tenant_id)
    if cursor is not None:
        anchor = await session.scalar(statement.where(Invoice.id == cursor))
        if anchor is None:
            raise DomainError("INVALID_INVOICE_CURSOR", "账单游标无效", 422)
        statement = statement.where(
            tuple_(Invoice.created_at, Invoice.id) < (anchor.created_at, anchor.id)
        )
    rows = (
        await session.scalars(
            statement.order_by(Invoice.created_at.desc(), Invoice.id.desc()).limit(limit + 1)
        )
    ).all()
    return InvoicePage(
        items=[InvoiceSummary.model_validate(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


async def invoice_detail(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> InvoiceDetail:
    invoice = await session.scalar(
        select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id)
    )
    if invoice is None:
        raise DomainError("INVOICE_NOT_FOUND", "账单不存在", 404)
    items = await session.scalars(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id).order_by(InvoiceItem.kind)
    )
    return InvoiceDetail(
        **InvoiceSummary.model_validate(invoice).model_dump(),
        items=[InvoiceLine.model_validate(item) for item in items],
    )
