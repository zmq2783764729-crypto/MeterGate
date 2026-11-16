# 用途：生成确定性模拟支付会话并验证签名覆盖的原始通知。
import hmac
from datetime import datetime
from uuid import UUID, uuid5

from pydantic import ValidationError

from app.core.errors import DomainError
from app.integrations.payments.base import PaymentNotification


def sign_webhook(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.digest(secret.encode(), timestamp.encode() + b"." + body, "sha256").hex()


class MockPaymentProvider:
    name = "mock"

    def __init__(self, secret: str) -> None:
        self.secret = secret

    def create_checkout(self, payment_id: UUID) -> UUID:
        return uuid5(payment_id, "metergate:mock-checkout")

    def verify_webhook(
        self, body: bytes, timestamp: str, signature: str, now: datetime
    ) -> PaymentNotification:
        if (
            not timestamp.isascii()
            or not timestamp.isdecimal()
            or len(timestamp) > 12
            or abs(now.timestamp() - int(timestamp)) > 300
            or not signature.isascii()
            or len(signature) != 64
            or not hmac.compare_digest(sign_webhook(self.secret, timestamp, body), signature)
        ):
            raise DomainError("INVALID_WEBHOOK_SIGNATURE", "付款回调签名无效或已过期", 401)
        try:
            return PaymentNotification.model_validate_json(body)
        except ValidationError as exc:
            raise DomainError("INVALID_PAYMENT_EVENT", "付款通知格式不正确", 422) from exc
