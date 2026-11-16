# 用途：通过异步会话查询和添加用户，写入时 flush 但不自行提交事务。
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def add_user(session: AsyncSession, *, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash)
    session.add(user)
    # flush 发送 INSERT，取回 UUID 与数据库生成时间；最终提交由 service 决定。
    await session.flush()
    return user
