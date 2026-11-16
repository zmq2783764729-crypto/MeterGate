# 用途：编排用户注册和密码认证，管理注册事务并将邮箱唯一冲突转换为业务错误。
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.errors import DomainError
from app.core.security import DUMMY_HASH, hash_password, invalid_credentials, verify_password
from app.modules.auth import repository
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest


def email_already_registered() -> DomainError:
    return DomainError("EMAIL_ALREADY_REGISTERED", "该邮箱已注册", 409)


async def register_user(session: AsyncSession, data: RegisterRequest) -> User:
    # Argon2 计算放在线程池，避免阻塞处理其他请求的异步事件循环。
    encoded_hash = await run_in_threadpool(hash_password, data.password.get_secret_value())
    try:
        async with session.begin():
            if await repository.get_user_by_email(session, str(data.email)) is not None:
                raise email_already_registered()
            user = await repository.add_user(
                session, email=str(data.email), password_hash=encoded_hash
            )
        return user
    except IntegrityError as exc:
        # 两个请求可能同时查到不存在；数据库唯一约束才是最终保障。
        # begin 上下文退出时已回滚，只将指定的邮箱冲突翻译为 409。
        driver_error = getattr(exc.orig, "__cause__", None)
        if getattr(driver_error, "constraint_name", None) == "uq_users_email":
            raise email_already_registered() from exc
        raise


async def authenticate_user(session: AsyncSession, data: LoginRequest) -> User:
    user = await repository.get_user_by_email(session, str(data.email))
    encoded_hash = user.password_hash if user is not None else DUMMY_HASH
    valid = await run_in_threadpool(verify_password, data.password.get_secret_value(), encoded_hash)
    if not valid or user is None:
        raise invalid_credentials()
    return user
