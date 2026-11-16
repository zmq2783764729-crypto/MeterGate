# 用途：校验注册登录输入、统一邮箱大小写，并定义不含密码哈希的用户与令牌响应。
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320, title="邮箱")
    password: SecretStr = Field(min_length=1, max_length=128, title="密码")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        # 本项目约定整个邮箱忽略大小写；注册与登录必须采用同一种规则。
        return value.lower()


class RegisterRequest(Credentials):
    password: SecretStr = Field(min_length=12, max_length=128, title="密码（12至128字符）")


class LoginRequest(Credentials):
    pass


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(title="用户编号")
    email: str = Field(title="邮箱")
    created_at: datetime = Field(title="创建时间")


class TokenResponse(BaseModel):
    access_token: str = Field(title="访问令牌", repr=False)
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(title="有效时长（秒）")
