# 用途：按账期保存后台生成的结算输入，确保重复投递只保存一次。
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SettlementInput(Base):
    __tablename__ = "settlement_inputs"

    period_id: Mapped[UUID] = mapped_column(
        ForeignKey("billing_periods.id", ondelete="RESTRICT"), primary_key=True
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="RESTRICT"), unique=True
    )
    total_quantity: Mapped[int] = mapped_column(BigInteger)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        ForeignKeyConstraint(
            ["period_id", "tenant_id"], ["billing_periods.id", "billing_periods.tenant_id"]
        ),
        CheckConstraint("status IN ('open', 'paid', 'void')", name="ck_invoices_status"),
        CheckConstraint("currency = 'CNY'", name="ck_invoices_currency"),
        CheckConstraint(
            "base_fee_cents >= 0 AND usage_fee_cents >= 0 "
            "AND total_cents = base_fee_cents + usage_fee_cents",
            name="ck_invoices_amounts",
        ),
        Index("ix_invoices_tenant_created", "tenant_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    period_id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid)
    plan_version_id: Mapped[UUID] = mapped_column(ForeignKey("plan_versions.id"))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(8), server_default=text("'open'"))
    base_fee_cents: Mapped[Decimal] = mapped_column(Numeric(40, 0))
    usage_fee_cents: Mapped[Decimal] = mapped_column(Numeric(40, 0))
    total_cents: Mapped[Decimal] = mapped_column(Numeric(40, 0))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (
        CheckConstraint("kind IN ('base', 'usage')", name="ck_invoice_items_kind"),
        CheckConstraint(
            "quantity >= 0 AND unit_price_cents >= 0 "
            "AND amount_cents = quantity * unit_price_cents",
            name="ck_invoice_items_amount",
        ),
    )

    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("invoices.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(8), primary_key=True)
    plan_version_id: Mapped[UUID] = mapped_column(ForeignKey("plan_versions.id"))
    quantity: Mapped[int] = mapped_column(BigInteger)
    unit_price_cents: Mapped[Decimal] = mapped_column(Numeric(40, 0))
    amount_cents: Mapped[Decimal] = mapped_column(Numeric(40, 0))
