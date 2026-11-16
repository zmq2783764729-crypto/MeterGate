# 用途：使用 Argon2 哈希验证密码，并按固定算法、签发方、接收方和期限签发校验访问令牌。
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.errors import DomainError

ALGORITHM = "HS256"
password_hasher = PasswordHash.recommended()
# 不存在的用户也执行一次密码验证，避免直接跳过昂贵计算。
DUMMY_HASH = password_hasher.hash("metergate-dummy-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hasher.verify(password, encoded_hash)


def require_jwt_secret(settings: Settings) -> str:
    secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret is not None else ""
    if len(secret.encode("utf-8")) < 32:
        raise DomainError(
            "AUTH_NOT_CONFIGURED", "认证服务尚未配置，请设置至少32字节的随机 JWT 密钥", 503
        )
    return secret


def invalid_credentials() -> DomainError:
    return DomainError(
        "INVALID_CREDENTIALS", "邮箱或密码错误", 401, headers={"WWW-Authenticate": "Bearer"}
    )


def invalid_token() -> DomainError:
    return DomainError(
        "INVALID_TOKEN",
        "访问令牌无效或已过期，请重新登录",
        401,
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(user_id: UUID, settings: Settings) -> str:
    secret = require_jwt_secret(settings)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "jti": uuid4().hex,
        "token_use": "access",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> UUID:
    secret = require_jwt_secret(settings)
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": ["sub", "iss", "aud", "iat", "nbf", "exp", "jti", "token_use"],
                "strict_aud": True,
            },
        )
        if claims["token_use"] != "access":
            raise invalid_token()
        return UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError) as exc:
        raise invalid_token() from exc
