# 用途：定义支付会话与回调的提供方适配契约。
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentNotification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    provider_reference: UUID
    status: Literal["pending", "failed", "succeeded"]
    amount_cents: int = Field(strict=True, ge=0, lt=10**40)
    currency: Literal["CNY"]


class PaymentProvider(Protocol):
    name: str

    def create_checkout(self, payment_id: UUID) -> UUID: ...

    def verify_webhook(
        self, body: bytes, timestamp: str, signature: str, now: datetime
    ) -> PaymentNotification: ...
