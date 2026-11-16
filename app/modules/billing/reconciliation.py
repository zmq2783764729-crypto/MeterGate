# 用途：只读核对事件、额度、计费明细及模拟付款记录。
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.billing.calculator import calculate_invoice
from app.modules.billing.models import Invoice, InvoiceItem
from app.modules.billing.schemas import InvoiceLine
from app.modules.metering.models import QuotaBucket, UsageEvent
from app.modules.payments.models import Payment
from app.modules.subscriptions.models import BillingPeriod, PeriodTerms


async def reconcile_period(session: AsyncSession, period_id: UUID) -> dict[str, object]:
    period = await session.get(BillingPeriod, period_id, with_for_update=True)
    if period is None:
        raise DomainError("PERIOD_NOT_FOUND", "账期不存在", 404)

    total = int(
        await session.scalar(
            select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
                UsageEvent.tenant_id == period.tenant_id, UsageEvent.period_id == period.id
            )
        )
    )
    bucket = await session.get(QuotaBucket, (period.tenant_id, period.id, "data_query"))
    terms = await session.get(PeriodTerms, period.id)
    invoice = await session.scalar(select(Invoice).where(Invoice.period_id == period.id))
    differences: list[dict[str, object]] = []

    def compare(field: str, expected: object, actual: object) -> None:
        if expected != actual:
            differences.append({"field": field, "expected": expected, "actual": actual})

    compare("quota.used", total, bucket.used if bucket else None)
    if terms is None:
        compare("period_terms", "present", None)
    elif bucket is not None:
        compare("quota.hard_limit", terms.hard_limit, bucket.hard_limit)
    if invoice is None:
        if period.status == "closed":
            compare("invoice", "present", None)
    elif terms is not None:
        expected = calculate_invoice(terms, total)
        compare("invoice.base_fee_cents", expected.base_fee_cents, int(invoice.base_fee_cents))
        compare("invoice.usage_fee_cents", expected.usage_fee_cents, int(invoice.usage_fee_cents))
        compare("invoice.total_cents", expected.total_cents, int(invoice.total_cents))
        compare("invoice.plan_version_id", str(terms.plan_version_id), str(invoice.plan_version_id))
        rows = await session.scalars(
            select(InvoiceItem)
            .where(InvoiceItem.invoice_id == invoice.id)
            .order_by(InvoiceItem.kind)
        )
        compare(
            "invoice.items",
            [line.model_dump(mode="json") for line in expected.items],
            [InvoiceLine.model_validate(line).model_dump(mode="json") for line in rows],
        )
        payment = await session.scalar(select(Payment).where(Payment.invoice_id == invoice.id))
        if payment is not None:
            compare(
                "mock_payment.amount_cents",
                int(invoice.total_cents),
                int(payment.expected_amount_cents),
            )
            compare("mock_payment.currency", invoice.currency, payment.currency)
        compare(
            "mock_payment.succeeded",
            invoice.status == "paid",
            payment is not None and payment.provider == "mock" and payment.status == "succeeded",
        )

    return {
        "period_id": str(period_id),
        "event_quantity": total,
        "consistent": not differences,
        "differences": differences,
    }
