# 用途：从账单创建或复用管理员的模拟支付会话。
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import DomainError
from app.integrations.payments.base import PaymentProvider
from app.integrations.payments.mock import MockPaymentProvider
from app.modules.billing.models import Invoice
from app.modules.payments.models import Payment
from app.modules.tenants.authorization import lock_and_authorize_admin
from app.modules.tenants.context import TenantContext


class CheckoutResult(BaseModel):
    payment_id: UUID
    provider: str
    provider_reference: UUID
    amount_cents: int
    currency: Literal["CNY"]


def payment_provider(settings: Settings) -> PaymentProvider:
    if settings.mock_webhook_secret is None:
        raise DomainError("PAYMENTS_UNAVAILABLE", "模拟支付尚未配置", 503)
    return MockPaymentProvider(settings.mock_webhook_secret.get_secret_value())


async def create_checkout(
    session: AsyncSession, context: TenantContext, invoice_id: UUID, provider: PaymentProvider
) -> CheckoutResult:
    async with session.begin():
        await lock_and_authorize_admin(session, context)
        invoice = await session.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.tenant_id == context.tenant_id)
            .with_for_update()
        )
        if invoice is None:
            raise DomainError("INVOICE_NOT_FOUND", "账单不存在", 404)
        if invoice.status != "open":
            raise DomainError("INVOICE_NOT_PAYABLE", "账单不处于可付款状态", 409)
        payment = await session.scalar(select(Payment).where(Payment.invoice_id == invoice.id))
        if payment is None:
            payment_id = uuid4()
            payment = Payment(
                id=payment_id,
                invoice_id=invoice.id,
                provider=provider.name,
                provider_reference=provider.create_checkout(payment_id),
                expected_amount_cents=invoice.total_cents,
                currency=invoice.currency,
            )
            session.add(payment)
            await session.flush()
        return CheckoutResult(
            payment_id=payment.id,
            provider=payment.provider,
            provider_reference=payment.provider_reference,
            amount_cents=int(payment.expected_amount_cents),
            currency=payment.currency,
        )
