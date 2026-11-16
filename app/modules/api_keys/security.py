# 用途：生成256位随机API Key并计算SHA-256摘要，解析格式且隐藏内存对象中的敏感值。
import hashlib
import re
import secrets
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import SecretStr

from app.core.errors import DomainError

TOKEN_PATTERN = re.compile(r"mgk_([0-9a-f]{32})_([A-Za-z0-9_-]{43})")


@dataclass(frozen=True)
class GeneratedApiKey:
    key_id: UUID
    prefix: str
    token: SecretStr
    token_digest: str = field(repr=False)


@dataclass(frozen=True)
class ApiKeyMaterial:
    key_id: UUID
    token_digest: str = field(repr=False)


def invalid_api_key() -> DomainError:
    return DomainError(
        "INVALID_API_KEY",
        "API Key无效、已过期或已撤销",
        401,
        headers={"WWW-Authenticate": "APIKey"},
    )


def generate_api_key() -> GeneratedApiKey:
    key_id = uuid4()
    token = f"mgk_{key_id.hex}_{secrets.token_urlsafe(32)}"
    return GeneratedApiKey(
        key_id=key_id,
        prefix=f"mgk_{key_id.hex[:8]}",
        token=SecretStr(token),
        token_digest=hashlib.sha256(token.encode("ascii")).hexdigest(),
    )


def parse_api_key(token: str | None) -> ApiKeyMaterial:
    if token is None or len(token) != 80:
        raise invalid_api_key()
    matched = TOKEN_PATTERN.fullmatch(token)
    if matched is None:
        raise invalid_api_key()
    return ApiKeyMaterial(
        key_id=UUID(hex=matched[1]), token_digest=hashlib.sha256(token.encode("ascii")).hexdigest()
    )
