# 用途：创建 FastAPI 应用、注册路由和中文错误响应，并管理 PostgreSQL 与 Redis 连接资源。
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis
from starlette.exceptions import HTTPException

from app import __version__
from app.api.router import router
from app.core.config import Settings
from app.core.errors import http_error, internal_error, validation_error
from app.db.session import create_db_engine, create_session_factory


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = application.state.settings
    try:
        # 每创建一份资源就登记清理，即使后续初始化失败也会释放此前资源。
        async with AsyncExitStack() as cleanup:
            if settings.database_url is not None:
                engine = create_db_engine(settings)
                cleanup.push_async_callback(engine.dispose)
                application.state.db_engine = engine
                application.state.session_factory = create_session_factory(engine)
            if settings.redis_url is not None:
                redis = Redis.from_url(
                    settings.redis_url.get_secret_value(),
                    decode_responses=True,
                    socket_connect_timeout=settings.health_timeout_seconds,
                    socket_timeout=settings.health_timeout_seconds,
                )
                cleanup.push_async_callback(redis.aclose)
                application.state.redis = redis
            # 连接是按需建立的；依赖不可用时让 live 继续响应，由 ready 返回 503。
            application.state.started = True
            yield
    finally:
        application.state.started = False
        application.state.db_engine = None
        application.state.session_factory = None
        application.state.redis = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    application = FastAPI(
        title=settings.app_name,
        description="MeterGate 企业服务计量与结算接口",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.started = False
    application.state.db_engine = None
    application.state.session_factory = None
    application.state.redis = None
    application.add_exception_handler(HTTPException, http_error)
    application.add_exception_handler(RequestValidationError, validation_error)
    application.add_exception_handler(Exception, internal_error)
    application.include_router(router)
    return application


app = create_app()
