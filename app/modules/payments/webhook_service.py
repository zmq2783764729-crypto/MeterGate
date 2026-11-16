# 用途：验签后按事件编号幂等处理模拟支付回调及账单状态。
from datetime import UTC, datetime
from hashlib import sha256

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.integrations.payments.base import PaymentProvider
from app.modules.audit.service import record_audit
from app.modules.billing.models import Invoice
from app.modules.payments.models import Payment, PaymentEvent


class WebhookResult(BaseModel):
    accepted: bool = True
    replayed: bool = False


async def process_webhook(
    session: AsyncSession, provider: PaymentProvider, body: bytes, timestamp: str, signature: str
) -> WebhookResult:
    now = datetime.now(UTC)
    notification = provider.verify_webhook(body, timestamp, signature, now)
    digest = sha256(body).hexdigest()
    async with session.begin():
        target = (
            await session.execute(
                select(Payment.id, Payment.invoice_id).where(
                    Payment.provider == provider.name,
                    Payment.provider_reference == notification.provider_reference,
                )
            )
        ).one_or_none()
        if target is None:
            raise DomainError("PAYMENT_NOT_FOUND", "未找到对应的支付会话", 404)
        invoice = await session.get(Invoice, target.invoice_id, with_for_update=True)
        payment = await session.get(Payment, target.id, with_for_update=True)
        if invoice is None or payment is None:
            raise RuntimeError("支付会话缺少关联账单")
        event_id = await session.scalar(
            insert(PaymentEvent)
            .values(
                provider=provider.name,
                event_id=notification.event_id,
                payment_id=payment.id,
                payload_hash=digest,
                status=notification.status,
            )
            .on_conflict_do_nothing(index_elements=[PaymentEvent.provider, PaymentEvent.event_id])
            .returning(PaymentEvent.event_id)
        )
        if event_id is None:
            existing = await session.get(PaymentEvent, (provider.name, notification.event_id))
            if (
                existing is None
                or existing.payload_hash != digest
                or existing.payment_id != payment.id
            ):
                raise DomainError("PAYMENT_EVENT_CONFLICT", "付款通知编号已用于其他内容", 409)
            return WebhookResult(replayed=True)
        if (
            payment.currency != notification.currency
            or invoice.currency != notification.currency
            or payment.expected_amount_cents != notification.amount_cents
            or invoice.total_cents != notification.amount_cents
        ):
            raise DomainError("PAYMENT_AMOUNT_MISMATCH", "付款金额或币种与账单不一致", 422)
        if invoice.status == "void":
            raise DomainError("INVOICE_NOT_PAYABLE", "账单不处于可付款状态", 409)
        if notification.status == "succeeded" and invoice.status == "open":
            payment.status = "succeeded"
            payment.paid_at = now
            invoice.status = "paid"
            record_audit(session, invoice.tenant_id, "invoice.paid", invoice.id)
        elif notification.status == "failed" and payment.status == "pending":
            payment.status = "failed"
        return WebhookResult()
