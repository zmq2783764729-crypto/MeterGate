# 用途：验证领域、HTTP、参数和未知错误的统一响应、请求编号一致性及敏感内容隐藏。
import asyncio

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_app
from app.middleware.request_context import get_request_id


@pytest.fixture
def error_application():
    application = create_app(Settings(_env_file=None))

    @application.get("/test-domain")
    async def fail_domain():
        raise DomainError("QUOTA_EXCEEDED", "本周期额度已用尽", 409)

    @application.get("/test-auth")
    async def require_authentication():
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})

    @application.get("/test-validation")
    async def validate_limit(limit: int):
        return {"limit": limit}

    @application.get("/test-internal")
    async def fail_unexpectedly():
        raise RuntimeError("synthetic-private-value")

    @application.get("/test-domain-header")
    async def fail_with_header():
        raise DomainError(
            "RATE_LIMITED",
            "请求过于频繁，请稍后重试",
            429,
            headers={"Retry-After": "10"},
        )

    return application


@pytest.mark.parametrize(
    ("path", "status", "code", "message"),
    [
        ("/test-domain", 409, "QUOTA_EXCEEDED", "本周期额度已用尽"),
        ("/test-auth", 401, "UNAUTHORIZED", "请先登录或提供有效的身份凭据"),
        ("/test-validation?limit=invalid", 422, "VALIDATION_ERROR", "请求参数校验失败"),
        ("/test-internal", 500, "INTERNAL_ERROR", "服务内部错误，请稍后重试"),
        ("/not-exist", 404, "NOT_FOUND", "请求的接口或资源不存在"),
    ],
)
def test_errors_share_contract_and_request_id(error_application, path, status, code, message):
    async def exercise():
        async with AsyncClient(
            transport=ASGITransport(app=error_application, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get(path)
        assert response.status_code == status
        payload = response.json()
        assert payload["code"] == code
        assert payload["message"] == message
        assert payload["request_id"] == response.headers["x-request-id"]
        assert "detail" not in payload
        assert "synthetic-private-value" not in response.text
        assert "invalid" not in response.text
        if status == 401:
            assert response.headers["www-authenticate"] == "Bearer"
        if status == 422:
            assert payload["errors"] == [
                {"field": "query.limit", "message": "参数格式或取值不正确"}
            ]
        assert get_request_id() is None

    asyncio.run(exercise())


def test_domain_and_http_headers_are_preserved(error_application):
    async def exercise():
        async with AsyncClient(
            transport=ASGITransport(app=error_application), base_url="http://test"
        ) as client:
            rate_limit = await client.get("/test-domain-header")
            method_error = await client.post("/health/live")
        assert rate_limit.status_code == 429
        assert rate_limit.headers["retry-after"] == "10"
        assert rate_limit.json()["request_id"] == rate_limit.headers["x-request-id"]
        assert method_error.status_code == 405
        assert "GET" in method_error.headers["allow"]
        assert method_error.json()["code"] == "METHOD_NOT_ALLOWED"
        assert method_error.json()["request_id"] == method_error.headers["x-request-id"]

    asyncio.run(exercise())
