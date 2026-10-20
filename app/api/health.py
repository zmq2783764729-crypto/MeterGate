# 用途：提供 live 存活检查和 PostgreSQL/Redis 的 ready 就绪检查，故障时返回 503 且隐藏凭据。
import asyncio
from typing import Literal

from fastapi import Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from app import __version__


class LiveResponse(BaseModel):
    status: Literal["正常"] = Field(title="运行状态")
    service: str = Field(title="服务名称")
    version: str = Field(title="版本号")


CheckStatus = Literal["正常", "不可用", "未配置"]


class ReadyResponse(BaseModel):
    status: Literal["已就绪", "未就绪"] = Field(title="就绪状态")
    checks: dict[str, CheckStatus] = Field(title="依赖检查结果")


async def check_database(request: Request) -> CheckStatus:
    engine = request.app.state.db_engine
    if engine is None:
        return "未配置"
    try:
        async with asyncio.timeout(request.app.state.settings.health_timeout_seconds):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return "正常"
    except Exception:
        # 就绪探针只报告依赖状态，不向响应或日志写入可能带凭据的异常文本。
        return "不可用"


async def check_redis(request: Request) -> CheckStatus:
    redis = request.app.state.redis
    if redis is None:
        return "未配置"
    try:
        async with asyncio.timeout(request.app.state.settings.health_timeout_seconds):
            return "正常" if await redis.ping() else "不可用"
    except Exception:
        return "不可用"


async def live(request: Request) -> LiveResponse:
    return LiveResponse(
        status="正常", service=request.app.state.settings.app_name, version=__version__
    )


async def ready(request: Request, response: Response) -> ReadyResponse:
    database_status, redis_status = await asyncio.gather(
        check_database(request), check_redis(request)
    )
    checks = {"database": database_status, "redis": redis_status}
    is_ready = request.app.state.started and all(value == "正常" for value in checks.values())
    response.status_code = 200 if is_ready else 503
    return ReadyResponse(status="已就绪" if is_ready else "未就绪", checks=checks)
