# 用途：验证应用配置互不串用、健康响应与配置显示不泄露测试密钥，以及生命周期正常结束。
import asyncio

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


def test_factories_isolate_configuration_and_release_lifespan():
    first = create_app(Settings(_env_file=None, app_name="first", jwt_secret="private-value"))
    second = create_app(Settings(_env_file=None, app_name="second"))

    async def exercise_applications():
        async with first.router.lifespan_context(first), second.router.lifespan_context(second):
            assert first.state.started and second.state.started
            async with (
                AsyncClient(
                    transport=ASGITransport(app=first), base_url="http://first"
                ) as first_client,
                AsyncClient(
                    transport=ASGITransport(app=second), base_url="http://second"
                ) as second_client,
            ):
                first_response = await first_client.get("/health/live")
                second_response = await second_client.get("/health/live")
                assert first_response.status_code == second_response.status_code == 200
                assert first_response.json()["service"] == "first"
                assert second_response.json()["service"] == "second"
                assert "private-value" not in first_response.text
                assert "private-value" not in str(first.state.settings)

    asyncio.run(exercise_applications())

    assert not first.state.started
    assert not second.state.started
