# 用途：校验密钥名称、权限和有效期，分开定义一次性完整密钥响应与普通公开元数据。
from datetime import UTC, datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.modules.api_keys.models import ApiKeyScope


class ApiKeyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, title="密钥名称")
    scopes: list[ApiKeyScope] = Field(min_length=1, max_length=2, title="允许的权限范围")
    expires_at: AwareDatetime | None = Field(default=None, title="到期时间，空值表示不设期限")

    @field_validator("scopes")
    @classmethod
    def unique_scopes(cls, values: list[ApiKeyScope]) -> list[ApiKeyScope]:
        if len(set(values)) != len(values):
            raise ValueError("权限范围不能重复")
        return values

    @field_validator("expires_at")
    @classmethod
    def future_expiry(cls, value: datetime | None) -> datetime | None:
        if value is not None and value <= datetime.now(UTC):
            raise ValueError("到期时间必须晚于当前时间")
        return value


class ApiKeyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(title="密钥编号")
    tenant_id: UUID = Field(title="所属企业")
    name: str = Field(title="密钥名称")
    prefix: str = Field(title="用于识别密钥的公开前缀")
    scopes: list[ApiKeyScope] = Field(title="权限范围")
    created_at: datetime = Field(title="创建时间")
    expires_at: datetime | None = Field(title="到期时间")
    revoked_at: datetime | None = Field(title="撤销时间")


class ApiKeyCreated(ApiKeyPublic):
    api_key: str = Field(title="完整API Key，仅本次创建时返回", repr=False)


class ApiKeyPage(BaseModel):
    items: list[ApiKeyPublic] = Field(title="企业密钥")
    next_cursor: UUID | None = Field(default=None, title="下一页游标")


class ApiKeyIdentity(BaseModel):
    key_id: UUID = Field(title="已认证密钥编号")
    tenant_id: UUID = Field(title="已认证企业编号")
    scopes: list[ApiKeyScope] = Field(title="密钥权限范围")
