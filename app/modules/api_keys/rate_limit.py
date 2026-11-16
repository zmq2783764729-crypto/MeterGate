# 用途：通过 Redis 原子计数为每个 API Key 执行固定窗口限流。
from typing import Annotated

from fastapi import Depends, Request
from redis.exceptions import RedisError

from app.core.errors import DomainError
from app.modules.api_keys.context import ApiKeyContext
from app.modules.api_keys.router import DemoReadKeyDependency, UsageWriteKeyDependency

COUNT_REQUEST = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('PTTL', KEYS[1])}
"""


async def _enforce(request: Request, context: ApiKeyContext) -> ApiKeyContext:
    settings = request.app.state.settings
    limit = settings.rate_limit_requests
    if limit == 0:
        return context
    redis = request.app.state.redis
    if redis is None:
        raise DomainError("RATE_LIMIT_UNAVAILABLE", "限流服务暂不可用", 503)
    try:
        count, ttl_ms = await redis.eval(
            COUNT_REQUEST,
            1,
            f"metergate:rate:{settings.environment}:{context.key_id}",
            settings.rate_limit_window_seconds,
        )
    except RedisError as exc:
        raise DomainError("RATE_LIMIT_UNAVAILABLE", "限流服务暂不可用", 503) from exc
    if count > limit:
        raise DomainError(
            "RATE_LIMIT_EXCEEDED",
            "请求过于频繁，请稍后重试",
            429,
            headers={"Retry-After": str(max(1, (ttl_ms + 999) // 1000))},
        )
    return context


async def _usage(request: Request, context: UsageWriteKeyDependency) -> ApiKeyContext:
    return await _enforce(request, context)


async def _demo(request: Request, context: DemoReadKeyDependency) -> ApiKeyContext:
    return await _enforce(request, context)


LimitedUsageKey = Annotated[ApiKeyContext, Depends(_usage)]
LimitedDemoKey = Annotated[ApiKeyContext, Depends(_demo)]
