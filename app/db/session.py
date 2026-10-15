# 用途：创建 PostgreSQL 异步连接池和会话工厂，为每次请求提供独立会话且不自动提交事务。
from collections.abc import AsyncIterator

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_db_engine(settings: Settings) -> AsyncEngine:
    if settings.database_url is None:
        raise ValueError("尚未配置数据库连接地址")
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "timeout": settings.health_timeout_seconds,
            "server_settings": {"timezone": "UTC"},
        },
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    if factory is None:
        raise HTTPException(status_code=503, detail="数据库尚未配置")
    # 会话结束会释放连接并回滚未提交事务；service 层显式决定 begin/commit。
    async with factory() as session:
        yield session
