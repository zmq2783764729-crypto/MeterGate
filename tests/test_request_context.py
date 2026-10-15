# 用途：验证请求编号在成功与错误响应中一致可查、每请求唯一、并发隔离且异常后正确清理。
import asyncio
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.middleware.request_context import get_request_id


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [("/health/live", 200), ("/missing", 404), ("/health/ready", 503)],
)
def test_normal_and_handled_error_responses_have_request_ids(path, expected_status):
    application = create_app(Settings(_env_file=None))

    async def exercise():
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                response = await client.get(path)
                assert response.status_code == expected_status
                assert UUID(response.headers["x-request-id"]).version == 4
        assert get_request_id() is None

    asyncio.run(exercise())


def test_each_request_gets_a_new_server_generated_id():
    application = create_app(Settings(_env_file=None))

    async def exercise():
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            first = await client.get("/health/live", headers={"X-Request-ID": "client-value"})
            second = await client.get("/health/live", headers={"X-Request-ID": "client-value"})
        assert first.headers["x-request-id"] != second.headers["x-request-id"]
        assert first.headers["x-request-id"] != "client-value"

    asyncio.run(exercise())


def test_concurrent_request_contexts_are_isolated():
    application = create_app(Settings(_env_file=None))

    @application.get("/test-context")
    async def inspect_context():
        before = get_request_id()
        await asyncio.sleep(0)
        assert get_request_id() == before
        return {"request_id": before}

    async def exercise():
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            responses = await asyncio.gather(*(client.get("/test-context") for _ in range(8)))
        request_ids = {response.headers["x-request-id"] for response in responses}
        assert len(request_ids) == 8
        for response in responses:
            assert response.json()["request_id"] == response.headers["x-request-id"]
        assert get_request_id() is None

    asyncio.run(exercise())


def test_validation_errors_keep_the_request_id():
    application = create_app(Settings(_env_file=None))

    @application.get("/test-validation")
    async def validate_limit(limit: int):
        return {"limit": limit}

    async def exercise():
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.get("/test-validation?limit=invalid")
        assert response.status_code == 422
        assert UUID(response.headers["x-request-id"]).version == 4
        assert get_request_id() is None

    asyncio.run(exercise())


def test_unexpected_errors_keep_id_and_clean_up_context():
    application = create_app(Settings(_env_file=None))
    observed = []

    @application.get("/test-failure")
    async def fail():
        observed.append(get_request_id())
        raise RuntimeError("synthetic-private-value")

    async def exercise():
        async with AsyncClient(
            transport=ASGITransport(app=application, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get("/test-failure")
            assert response.status_code == 500
            assert response.headers["x-request-id"] == observed[0]
            assert "synthetic-private-value" not in response.text
            assert get_request_id() is None
            following = await client.get("/health/live")
            assert following.status_code == 200
            assert following.headers["x-request-id"] != observed[0]
        assert get_request_id() is None

    asyncio.run(exercise())
