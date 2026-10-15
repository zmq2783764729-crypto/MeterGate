# 用途：验证请求与错误日志的编号关联、并发隔离、字段安全、日志级别及重复配置行为。
import asyncio
import io
import json
import logging

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.main import create_app
from app.middleware.request_context import get_request_id


@pytest.fixture
def captured_logs(monkeypatch):
    names = ["metergate", "metergate.http", "uvicorn.error", "uvicorn.access"]
    saved = {
        name: (logger.handlers[:], logger.level, logger.propagate, logger.disabled)
        for name in names
        for logger in [logging.getLogger(name)]
    }
    output = io.StringIO()
    monkeypatch.setattr(
        "app.main.configure_logging", lambda level: configure_logging(level, stream=output)
    )
    yield output
    for name, (handlers, level, propagate, disabled) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers = handlers
        logger.setLevel(level)
        logger.propagate = propagate
        logger.disabled = disabled


def records(output):
    return [json.loads(line) for line in output.getvalue().splitlines()]


@pytest.mark.parametrize(
    ("path", "status", "level", "code"),
    [
        ("/health/live", 200, "INFO", None),
        ("/not-exist", 404, "WARNING", "NOT_FOUND"),
        ("/test-domain", 409, "WARNING", "QUOTA_EXCEEDED"),
        ("/test-failure", 500, "ERROR", "INTERNAL_ERROR"),
    ],
)
def test_request_logs_match_response_id_and_status(captured_logs, path, status, level, code):
    application = create_app(Settings(_env_file=None))

    @application.get("/test-domain")
    async def fail_domain():
        raise DomainError("QUOTA_EXCEEDED", "本周期额度已用尽", 409)

    @application.get("/test-failure")
    async def fail_unexpectedly():
        raise RuntimeError("synthetic-error-secret")

    async def exercise():
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=ASGITransport(app=application, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                response = await client.get(path)
        return response

    response = asyncio.run(exercise())
    assert response.status_code == status
    entries = records(captured_logs)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["request_id"] == response.headers["x-request-id"]
    assert entry["status_code"] == status
    assert entry["level"] == level
    assert entry["duration_ms"] >= 0
    assert entry.get("code") == code
    assert entry["timestamp"].endswith("+00:00")
    if status >= 400:
        assert response.json()["request_id"] == entry["request_id"]
    if status == 500:
        assert entry["event"] == "request_failed"
        assert entry["error_type"] == "RuntimeError"
    assert "synthetic-error-secret" not in captured_logs.getvalue()


def test_request_secrets_and_path_values_are_not_logged(captured_logs):
    application = create_app(Settings(_env_file=None))

    @application.post("/test-input/{resource_id}")
    async def accept_input(resource_id: str, request: Request):
        assert (await request.json())["password"] == "synthetic-password-secret"
        return {"accepted": True}

    async def exercise():
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/test-input/synthetic-path-secret?token=synthetic-query-secret",
                    headers={
                        "Authorization": "Bearer synthetic-jwt-secret",
                        "X-API-Key": "synthetic-api-key-secret",
                        "X-Request-ID": "synthetic-client-id-secret",
                    },
                    json={"password": "synthetic-password-secret"},
                )
                unmatched = await client.get("/synthetic-unmatched-secret")
        return response, unmatched

    response, unmatched = asyncio.run(exercise())
    assert response.status_code == 200 and unmatched.status_code == 404
    entries = records(captured_logs)
    assert entries[0]["route"] == "/test-input/{resource_id}"
    assert entries[1]["route"] == "<unmatched>"
    assert "synthetic-" not in captured_logs.getvalue()


def test_concurrent_logs_keep_their_request_ids(captured_logs):
    application = create_app(Settings(_env_file=None))

    @application.get("/test-context")
    async def inspect_context():
        request_id = get_request_id()
        await asyncio.sleep(0)
        return {"request_id": request_id}

    async def exercise():
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                return await asyncio.gather(*(client.get("/test-context") for _ in range(8)))

    responses = asyncio.run(exercise())
    by_id = {entry["request_id"]: entry for entry in records(captured_logs)}
    assert len(by_id) == 8
    for response in responses:
        request_id = response.headers["x-request-id"]
        assert request_id == response.json()["request_id"]
        assert by_id[request_id]["status_code"] == 200


def test_server_exception_text_and_access_urls_are_not_logged(captured_logs):
    configure_logging("INFO", stream=captured_logs)
    try:
        raise RuntimeError("synthetic-server-secret")
    except RuntimeError:
        logging.getLogger("uvicorn.error").exception("synthetic-log-message-secret")
    logging.getLogger("uvicorn.access").info("GET /?token=synthetic-access-secret")
    entry = records(captured_logs)[0]
    assert entry["event"] == "server_event"
    assert entry["error_type"] == "RuntimeError"
    assert len(records(captured_logs)) == 1
    assert "synthetic-" not in captured_logs.getvalue()


def test_reconfiguration_does_not_duplicate_handlers_or_change_root(captured_logs):
    root_handlers = logging.getLogger().handlers[:]
    configure_logging("INFO", stream=captured_logs)
    configure_logging("INFO", stream=captured_logs)
    assert len(logging.getLogger("metergate").handlers) == 1
    assert len(logging.getLogger("uvicorn.error").handlers) == 1
    assert logging.getLogger().handlers == root_handlers
    logging.getLogger("metergate.http").info("synthetic-private-message")
    assert len(records(captured_logs)) == 1
    assert "synthetic-private-message" not in captured_logs.getvalue()


def test_configured_log_level_filters_lower_levels(captured_logs):
    configure_logging("ERROR", stream=captured_logs)
    logger = logging.getLogger("metergate.http")
    logger.info("synthetic-info-secret")
    logger.warning("synthetic-warning-secret")
    logger.error("synthetic-error-secret")
    entries = records(captured_logs)
    assert len(entries) == 1
    assert entries[0]["level"] == "ERROR"
    assert "synthetic-" not in captured_logs.getvalue()
