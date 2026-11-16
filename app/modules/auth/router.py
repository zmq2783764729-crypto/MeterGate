# 用途：提供 main.py 顶层认证接口调用的处理函数，以及会话和配置依赖类型。
from typing import Annotated

from fastapi import Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_access_token, require_jwt_secret
from app.db.session import get_session
from app.dependencies.auth import get_settings
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.auth.service import authenticate_user, register_user

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


async def register(data: RegisterRequest, session: SessionDependency) -> User:
    return await register_user(session, data)


async def login(
    data: LoginRequest,
    response: Response,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    require_jwt_secret(settings)
    user = await authenticate_user(session, data)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(
        access_token=create_access_token(user.id, settings),
        expires_in=settings.access_token_minutes * 60,
    )
