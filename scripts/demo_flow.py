# 用途：在专用演示库运行两企业、并发计量、异步出账和模拟付款闭环。
import argparse
import asyncio
import json
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.session import create_db_engine, create_session_factory
from app.integrations.payments.base import PaymentNotification
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.catalog.service import seed_catalog
from app.modules.metering.schemas import MAX_USAGE_QUANTITY
from app.modules.subscriptions.period_service import resolve_open_period
from app.modules.tenants import models as tenant_models  # noqa: F401
from scripts.send_mock_webhook import send_notification


def request(client: httpx.Client, method: str, path: str, expected: int, **options) -> dict:
    response = client.request(method, path, **options)
    if response.status_code != expected:
        code = response.json().get("code", "UNKNOWN")
        raise RuntimeError(f"{method} {path} 返回 {response.status_code} {code}")
    return response.json()


def create_enterprise(client: httpx.Client, name: str, version_id: str) -> tuple:
    credentials = {
        "email": f"demo-{uuid4().hex}@example.com",
        "password": secrets.token_urlsafe(30),
    }
    request(client, "POST", "/v1/auth/register", 201, json=credentials)
    login = request(client, "POST", "/v1/auth/login", 200, json=credentials)
    admin = {"Authorization": f"Bearer {login['access_token']}"}
    tenant = request(client, "POST", "/v1/tenants", 201, headers=admin, json={"name": name})
    route = f"/v1/tenants/{tenant['id']}"
    subscription = request(
        client,
        "POST",
        route + "/subscription",
        201,
        headers=admin,
        json={"plan_version_id": version_id},
    )
    key = request(
        client,
        "POST",
        route + "/api-keys",
        201,
        headers=admin,
        json={"name": "演示计量", "scopes": ["usage:write"]},
    )
    return route, tenant["id"], admin, subscription["current_period"], key["api_key"]


async def prepare(
    settings: Settings, tenant_id: UUID | None = None, end: datetime | None = None
) -> None:
    engine = create_db_engine(settings)
    try:
        factory = create_session_factory(engine)
        async with factory() as session:
            if tenant_id is None:
                await seed_catalog(session)
            elif end is not None:
                async with session.begin():
                    await resolve_open_period(session, tenant_id, end)
    finally:
        await engine.dispose()


def run(settings: Settings, base_url: str, wait_seconds: int, secret: str) -> dict:
    asyncio.run(prepare(settings))
    with httpx.Client(base_url=base_url, timeout=15, trust_env=False) as client:
        plans = request(client, "GET", "/v1/plans", 200)["items"]
        version = next(
            (
                item["latest_version"]
                for item in plans
                if 0 < item["latest_version"]["hard_limit"] <= MAX_USAGE_QUANTITY
            ),
            None,
        )
        if version is None:
            raise RuntimeError("缺少支持本次并发演示的套餐")
        root, tenant, admin, period, api_key = create_enterprise(
            client, "演示企业 A", version["id"]
        )
        other_root, other_tenant, other_admin, _, _ = create_enterprise(
            client, "演示企业 B", version["id"]
        )
        request(client, "GET", root + "/subscription", 404, headers=other_admin)
        quota = period["terms"]["hard_limit"]

        def submit(_: int) -> httpx.Response:
            return client.post(
                "/v1/usage/events",
                headers={"X-API-Key": api_key},
                json={
                    "event_id": str(uuid4()),
                    "metric": "data_query",
                    "quantity": quota,
                    "occurred_at": datetime.now(UTC).isoformat(),
                },
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(submit, range(4)))
        if sorted(item.status_code for item in responses) != [200, 409, 409, 409]:
            raise RuntimeError("并发上报未得到预期的额度结果")
        if any(
            item.status_code == 409 and item.json()["code"] != "QUOTA_EXCEEDED"
            for item in responses
        ):
            raise RuntimeError("并发拒绝并非额度不足")

        asyncio.run(prepare(settings, UUID(tenant), datetime.fromisoformat(period["period_end"])))
        deadline = time.monotonic() + wait_seconds
        while True:
            result = request(client, "GET", root + "/invoices", 200, headers=admin)
            row = next((row for row in result["items"] if row["period_id"] == period["id"]), None)
            if row is not None:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("未等到账单，请确认 Outbox 与 Worker 已启动")
            time.sleep(0.5)
        invoice_id = row["id"]
        request(client, "GET", f"{other_root}/invoices/{invoice_id}", 404, headers=other_admin)
        invoice_path = f"{root}/invoices/{invoice_id}"
        invoice = request(client, "GET", invoice_path, 200, headers=admin)
        expected = period["terms"]["base_fee_cents"] + quota * period["terms"]["unit_price_cents"]
        if invoice["total_cents"] != expected:
            raise RuntimeError("账单金额与原账期价格快照不一致")
        checkout = request(client, "POST", invoice_path + "/checkout", 200, headers=admin)
        notification = PaymentNotification(
            event_id=uuid4(),
            provider_reference=checkout["provider_reference"],
            status="succeeded",
            amount_cents=checkout["amount_cents"],
            currency="CNY",
        )
        replies = [json.loads(send_notification(base_url, notification, secret)) for _ in range(3)]
        if [reply["replayed"] for reply in replies] != [False, True, True]:
            raise RuntimeError("模拟付款通知重放结果不一致")
        paid = request(client, "GET", invoice_path, 200, headers=admin)
        if paid["status"] != "paid":
            raise RuntimeError("账单未完成模拟付款")
        return {
            "tenant_id": tenant,
            "other_tenant_id": other_tenant,
            "period_id": period["id"],
            "invoice_id": invoice_id,
            "status": paid["status"],
            "total_cents": paid["total_cents"],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行本地 MeterGate 演示闭环")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--wait", type=int, default=30)
    args = parser.parse_args()
    settings = Settings()
    db = settings.database_url
    url = urlsplit(args.url)
    if url.scheme not in {"http", "https"} or url.hostname not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("演示仅支持本地 API")
    if (
        settings.environment == "production"
        or db is None
        or not (make_url(db.get_secret_value()).database or "").startswith("metergate_demo_")
    ):
        parser.error("请使用非生产环境的 metergate_demo_ 专用数据库")
    if settings.mock_webhook_secret is None:
        parser.error("请配置模拟回调密钥")
    if not 1 <= args.wait <= 300:
        parser.error("等待时间须在 1 到 300 秒之间")
    print(
        json.dumps(
            run(settings, args.url, args.wait, settings.mock_webhook_secret.get_secret_value())
        )
    )


if __name__ == "__main__":
    main()
