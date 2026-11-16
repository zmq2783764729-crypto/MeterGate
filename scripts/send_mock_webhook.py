# 用途：用本机配置签署并发送模拟支付通知。
import argparse
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from app.core.config import Settings
from app.integrations.payments.base import PaymentNotification
from app.integrations.payments.mock import sign_webhook


def send_notification(base_url: str, notification: PaymentNotification, secret: str) -> str:
    body = notification.model_dump_json().encode()
    timestamp = str(int(time.time()))
    request = Request(
        base_url.rstrip("/") + "/v1/webhooks/payments/mock",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Mock-Timestamp": timestamp,
            "X-Mock-Signature": sign_webhook(secret, timestamp, body),
        },
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return response.read().decode()


def main() -> None:
    parser = argparse.ArgumentParser(description="发送模拟支付通知")
    parser.add_argument("reference", type=UUID)
    parser.add_argument("amount_cents", type=int)
    parser.add_argument("--event-id", type=UUID, default=uuid4())
    parser.add_argument("--status", choices=["succeeded", "failed", "pending"], default="succeeded")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    url = urlsplit(args.url)
    if url.scheme not in {"http", "https"} or url.hostname not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("仅允许本机付款模拟服务")
    secret = Settings().mock_webhook_secret
    if secret is None:
        parser.error("请配置 MG_MOCK_WEBHOOK_SECRET")
    notification = PaymentNotification(
        event_id=args.event_id,
        amount_cents=args.amount_cents,
        status=args.status,
        provider_reference=args.reference,
        currency="CNY",
    )
    print(send_notification(args.url, notification, secret.get_secret_value()))


if __name__ == "__main__":
    main()
