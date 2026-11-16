# 用途：定义账单金额、明细及可复核的整数分计价结果。
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InvoiceLine(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: Literal["base", "usage"]
    plan_version_id: UUID
    quantity: int
    unit_price_cents: int
    amount_cents: int


class InvoiceDraft(BaseModel):
    base_fee_cents: int
    usage_fee_cents: int
    total_cents: int
    items: tuple[InvoiceLine, InvoiceLine]


class InvoiceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    period_id: UUID
    plan_version_id: UUID
    currency: Literal["CNY"]
    status: Literal["open", "paid", "void"]
    base_fee_cents: int
    usage_fee_cents: int
    total_cents: int
    created_at: datetime


class InvoiceDetail(InvoiceSummary):
    items: list[InvoiceLine]


class InvoicePage(BaseModel):
    items: list[InvoiceSummary]
    next_cursor: UUID | None = None
