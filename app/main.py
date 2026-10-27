# 用途：在模块顶层使用 @app 定义接口，并配置应用工厂、错误处理、日志及数据库和 Redis 生命周期。
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis
from starlette.exceptions import HTTPException

from app import __version__
from app.api.health import LiveResponse, ReadyResponse
from app.api.health import live as health_live
from app.api.health import ready as health_ready
from app.api.router import copy_routes
from app.core.config import Settings
from app.core.errors import DomainError, domain_error, http_error, internal_error, validation_error
from app.core.logging import configure_logging
from app.db.session import create_db_engine, create_session_factory
from app.dependencies.auth import get_current_user
from app.middleware.request_context import RequestContextMiddleware
from app.modules.auth.models import User
from app.modules.auth.router import SessionDependency, SettingsDependency
from app.modules.auth.router import login as auth_login
from app.modules.auth.router import register as auth_register
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.modules.tenants.router import (
    AdminTenantDependency,
    CurrentUserDependency,
    TenantContextDependency,
    TenantSessionDependency,
)
from app.modules.tenants.router import add_member as tenant_add_member
from app.modules.tenants.router import create_tenant as tenant_create
from app.modules.tenants.router import delete_member as tenant_delete_member
from app.modules.tenants.router import list_members as tenant_list_members
from app.modules.tenants.router import list_tenants as tenant_list
from app.modules.tenants.router import update_member as tenant_update_member
from app.modules.tenants.schemas import (
    MemberAddRequest,
    MemberPage,
    MemberPublic,
    MemberRoleRequest,
    TenantCreateRequest,
    TenantPage,
    TenantPublic,
)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = application.state.settings
    configure_logging(settings.log_level)
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


def _build_app(settings: Settings | None = None) -> FastAPI:
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
    application.add_middleware(RequestContextMiddleware)
    application.add_exception_handler(DomainError, domain_error)
    application.add_exception_handler(HTTPException, http_error)
    application.add_exception_handler(RequestValidationError, validation_error)
    application.add_exception_handler(Exception, internal_error)
    return application


app = _build_app()


@app.get(
    "/health/live",
    tags=["健康检查"],
    response_model=LiveResponse,
    summary="检查服务是否存活",
    description="返回服务运行状态、名称与版本，不检查数据库和 Redis。",
    responses={200: {"description": "服务正常响应"}},
)
async def live(request: Request) -> LiveResponse:
    return await health_live(request)


@app.get(
    "/health/ready",
    tags=["健康检查"],
    response_model=ReadyResponse,
    summary="检查服务是否就绪",
    description="检查 PostgreSQL 与 Redis，任一项未配置或不可用时返回 503。",
    responses={
        200: {"description": "所有依赖正常，服务已就绪"},
        503: {"description": "依赖未配置或不可用，服务未就绪", "model": ReadyResponse},
    },
)
async def ready(request: Request, response: Response) -> ReadyResponse:
    return await health_ready(request, response)


@app.post(
    "/v1/auth/register",
    tags=["用户认证"],
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="注册用户",
)
async def register(data: RegisterRequest, session: SessionDependency) -> User:
    return await auth_register(data, session)


@app.post("/v1/auth/login", tags=["用户认证"], response_model=TokenResponse, summary="邮箱密码登录")
async def login(
    data: LoginRequest,
    response: Response,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    return await auth_login(data, response, session, settings)


@app.get("/v1/auth/me", tags=["用户认证"], response_model=UserPublic, summary="查看当前登录用户")
async def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@app.post(
    "/v1/tenants",
    tags=["企业管理"],
    response_model=TenantPublic,
    status_code=status.HTTP_201_CREATED,
    summary="创建企业并成为管理员",
)
async def create_tenant(
    data: TenantCreateRequest, user: CurrentUserDependency, session: TenantSessionDependency
) -> TenantPublic:
    return await tenant_create(data, user, session)


@app.get("/v1/tenants", tags=["企业管理"], response_model=TenantPage, summary="查询我加入的企业")
async def list_tenants(
    user: CurrentUserDependency,
    session: TenantSessionDependency,
    limit: Annotated[int, Query(ge=1, le=100, title="每页条数")] = 20,
    cursor: Annotated[UUID | None, Query(title="上一页返回的 next_cursor")] = None,
) -> TenantPage:
    return await tenant_list(user, session, limit, cursor)


@app.post(
    "/v1/tenants/{tenant_id}/members",
    tags=["企业成员"],
    response_model=MemberPublic,
    status_code=status.HTTP_201_CREATED,
    summary="添加已注册用户为企业成员",
)
async def add_member(
    data: MemberAddRequest, context: AdminTenantDependency, session: TenantSessionDependency
) -> MemberPublic:
    return await tenant_add_member(data, context, session)


@app.get(
    "/v1/tenants/{tenant_id}/members",
    tags=["企业成员"],
    response_model=MemberPage,
    summary="查询本企业成员",
)
async def list_members(
    context: TenantContextDependency,
    session: TenantSessionDependency,
    limit: Annotated[int, Query(ge=1, le=100, title="每页条数")] = 20,
    cursor: Annotated[UUID | None, Query(title="上一页返回的 next_cursor")] = None,
) -> MemberPage:
    return await tenant_list_members(context, session, limit, cursor)


@app.patch(
    "/v1/tenants/{tenant_id}/members/{user_id}",
    tags=["企业成员"],
    response_model=MemberPublic,
    summary="修改企业成员角色",
)
async def update_member(
    user_id: UUID,
    data: MemberRoleRequest,
    context: AdminTenantDependency,
    session: TenantSessionDependency,
) -> MemberPublic:
    return await tenant_update_member(user_id, data, context, session)


@app.delete(
    "/v1/tenants/{tenant_id}/members/{user_id}",
    tags=["企业成员"],
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="移除企业成员",
)
async def delete_member(
    user_id: UUID, context: AdminTenantDependency, session: TenantSessionDependency
) -> Response:
    await tenant_delete_member(user_id, context, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def create_app(settings: Settings | None = None) -> FastAPI:
    """为测试或独立运行创建另一份应用，复用上方接口定义。"""
    application = _build_app(settings)
    copy_routes(application, app)
    return application
