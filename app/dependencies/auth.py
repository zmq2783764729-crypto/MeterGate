# 用途：注入认证配置，验证 Bearer 访问令牌，并从数据库加载当前登录用户。
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import decode_access_token, invalid_token
from app.db.session import get_session
from app.modules.auth.models import User
from app.modules.auth.repository import get_user_by_id

bearer = HTTPBearer(auto_error=False, scheme_name="访问令牌", description="登录获得的 Bearer JWT")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_token_subject(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UUID:
    if credentials is None:
        raise invalid_token()
    return decode_access_token(credentials.credentials, settings)


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_token_subject)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise invalid_token()
    return user
