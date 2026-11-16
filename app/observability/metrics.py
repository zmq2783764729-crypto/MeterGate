# 用途：采集低基数 HTTP 指标和来自数据库的 Outbox 状态。
import hmac
from datetime import UTC, datetime

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import Scope

from app.core.errors import DomainError
from app.core.logging import HTTP_METHODS
from app.modules.billing.events import PERIOD_CLOSED
from app.modules.billing.models import Invoice
from app.workers.outbox_models import OutboxEvent

registry = CollectorRegistry()
http_requests = Counter(
    "metergate_http_requests", "HTTP requests", ["method", "route", "status"], registry=registry
)
http_duration = Histogram(
    "metergate_http_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
    registry=registry,
)
quota_denials = Counter("metergate_quota_denials", "Quota denials", registry=registry)
usage_replays = Counter("metergate_usage_replays", "Committed usage replays", registry=registry)


def observe_request(scope: Scope, status: int, duration: float) -> None:
    route = getattr(scope.get("route"), "path", "<unmatched>")
    if route == "/metrics":
        return
    method = scope.get("method")
    method = method if method in HTTP_METHODS else "OTHER"
    http_requests.labels(method, route, str(status)).inc()
    http_duration.labels(method, route).observe(duration)
    if scope.get("state", {}).get("error_code") == "QUOTA_EXCEEDED":
        quota_denials.inc()


async def render_metrics(request: Request) -> Response:
    settings = request.app.state.settings
    token = settings.metrics_token
    if token is None:
        raise DomainError("METRICS_DISABLED", "指标端点未启用", 404)
    credential = request.headers.get("authorization", "")
    if not hmac.compare_digest(credential.encode(), f"Bearer {token.get_secret_value()}".encode()):
        raise DomainError("METRICS_UNAUTHORIZED", "指标访问凭据无效", 401)
    factory = request.app.state.session_factory
    if factory is None:
        raise DomainError("METRICS_UNAVAILABLE", "指标数据暂不可用", 503)
    billing_pending = and_(
        OutboxEvent.topic == PERIOD_CLOSED,
        OutboxEvent.published_at.is_not(None),
        OutboxEvent.failed_at.is_(None),
        ~select(Invoice.id).where(Invoice.period_id == OutboxEvent.aggregate_id).exists(),
    )
    try:
        async with factory() as session:
            counts = (
                await session.execute(
                    select(
                        func.count().filter(
                            OutboxEvent.published_at.is_(None), OutboxEvent.failed_at.is_(None)
                        ),
                        func.count().filter(OutboxEvent.failed_at.is_not(None)),
                        func.min(OutboxEvent.next_attempt_at).filter(
                            OutboxEvent.published_at.is_(None), OutboxEvent.failed_at.is_(None)
                        ),
                        func.count().filter(billing_pending),
                        func.min(OutboxEvent.published_at).filter(billing_pending),
                    )
                )
            ).one()
    except SQLAlchemyError as exc:
        raise DomainError("METRICS_UNAVAILABLE", "指标数据暂不可用", 503) from exc
    snapshot = CollectorRegistry()
    pending, failed, oldest, queued, oldest_queued = counts
    now = datetime.now(UTC)
    age_seconds = max(0.0, (now - oldest).total_seconds()) if oldest else 0.0
    queue_age = max(0.0, (now - oldest_queued).total_seconds()) if oldest_queued else 0.0
    for name, description, value in (
        ("metergate_outbox_pending", "Outbox events pending publication", pending),
        ("metergate_outbox_failed", "Outbox events with exhausted retries", failed),
        ("metergate_outbox_oldest_due_seconds", "Age of the oldest due outbox event", age_seconds),
        ("metergate_billing_pending", "Published billing events without an invoice", queued),
        ("metergate_billing_oldest_pending_seconds", "Age of the oldest queued invoice", queue_age),
    ):
        Gauge(name, description, registry=snapshot).set(value)
    return Response(
        generate_latest(registry) + generate_latest(snapshot),
        headers={"Content-Type": CONTENT_TYPE_LATEST, "Cache-Control": "no-store"},
    )
