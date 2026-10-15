# 用途：验证就绪检查的故障、超时与脱敏行为，以及连接资源在正常和异常路径下正确释放。
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def runtime(monkeypatch):
    connection = MagicMock()
    connection.execute = AsyncMock()
    engine = MagicMock()
    engine.connect.return_value.__aenter__.return_value = connection
    engine.dispose = AsyncMock()
    redis = MagicMock()
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    monkeypatch.setattr("app.main.create_db_engine", lambda settings: engine)
    monkeypatch.setattr("app.main.create_session_factory", lambda resource: MagicMock())
    monkeypatch.setattr("app.main.Redis.from_url", lambda *args, **kwargs: redis)
    application = create_app(
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://user:synthetic-secret@localhost/db",
            redis_url="redis://localhost/0",
            health_timeout_seconds=0.05,
        )
    )
    return application, engine, connection, redis


def test_readiness_without_configuration_is_503_and_live_is_200():
    application = create_app(Settings(_env_file=None))

    async def exercise():
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                response = await client.get("/health/ready")
                assert response.status_code == 503
                assert response.json() == {
                    "status": "未就绪",
                    "checks": {"database": "未配置", "redis": "未配置"},
                }
                assert (await client.get("/health/live")).status_code == 200

    asyncio.run(exercise())


@pytest.mark.parametrize("failure", [None, "database", "redis", "timeout"])
def test_readiness_and_cleanup_on_dependency_failures(runtime, failure):
    application, engine, connection, redis = runtime
    if failure == "database":
        connection.execute.side_effect = RuntimeError("synthetic-secret connection failure")
    elif failure == "redis":
        redis.ping.side_effect = RuntimeError("synthetic-secret redis failure")
    elif failure == "timeout":

        async def stalled_query(*args, **kwargs):
            await asyncio.sleep(10)

        connection.execute.side_effect = stalled_query

    async def exercise():
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                response = await client.get("/health/ready")
                assert response.status_code == (200 if failure is None else 503)
                assert "synthetic-secret" not in response.text
                checks = response.json()["checks"]
                assert checks["database"] == (
                    "不可用" if failure in {"database", "timeout"} else "正常"
                )
                assert checks["redis"] == ("不可用" if failure == "redis" else "正常")
                assert (await client.get("/health/live")).status_code == 200
        assert not application.state.started
        assert application.state.db_engine is None
        assert application.state.session_factory is None
        assert application.state.redis is None

    asyncio.run(exercise())
    engine.dispose.assert_awaited_once()
    redis.aclose.assert_awaited_once()


def test_partial_initialization_failure_releases_created_engine(runtime, monkeypatch):
    application, engine, _, redis = runtime

    def invalid_redis_url(*args, **kwargs):
        raise ValueError("synthetic initialization failure")

    monkeypatch.setattr("app.main.Redis.from_url", invalid_redis_url)

    async def exercise():
        with pytest.raises(ValueError, match="synthetic initialization failure"):
            async with application.router.lifespan_context(application):
                pytest.fail("Application should not enter running state")
        assert not application.state.started
        assert application.state.db_engine is application.state.session_factory is None

    asyncio.run(exercise())
    engine.dispose.assert_awaited_once()
    redis.aclose.assert_not_awaited()


def test_redis_cleanup_error_still_releases_database_engine(runtime):
    application, engine, _, redis = runtime
    redis.aclose.side_effect = RuntimeError("synthetic cleanup failure")

    async def exercise():
        with pytest.raises(RuntimeError, match="synthetic cleanup failure"):
            async with application.router.lifespan_context(application):
                assert application.state.started
        assert not application.state.started
        assert application.state.redis is application.state.db_engine is None

    asyncio.run(exercise())
    redis.aclose.assert_awaited_once()
    engine.dispose.assert_awaited_once()
