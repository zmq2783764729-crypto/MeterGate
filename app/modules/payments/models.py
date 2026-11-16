# 用途：保存模拟支付会话、预期金额和付款处理状态。
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'failed', 'succeeded')", name="ck_payments_status"),
        CheckConstraint(
            "expected_amount_cents >= 0 AND currency = 'CNY'", name="ck_payments_amount"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("invoices.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(20))
    provider_reference: Mapped[UUID] = mapped_column(Uuid, unique=True)
    expected_amount_cents: Mapped[Decimal] = mapped_column(Numeric(40, 0))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(10), server_default=text("'pending'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    provider: Mapped[str] = mapped_column(String(20), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id"), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(10))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
