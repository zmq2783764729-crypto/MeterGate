# 用途：为 Outbox 发布器和 Dramatiq Worker 连接同一个 Redis 队列。
from dramatiq.brokers.redis import RedisBroker
from redis import Redis

from app.core.config import Settings

settings = Settings()
if settings.redis_url is None:
    raise RuntimeError("后台任务需要配置 MG_REDIS_URL")

broker = RedisBroker(
    client=Redis.from_url(
        settings.redis_url.get_secret_value(), socket_timeout=5, socket_connect_timeout=5
    ),
    namespace=f"metergate:{settings.environment}",
)
