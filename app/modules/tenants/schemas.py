# 用途：校验企业和成员请求，定义企业、成员及items/next_cursor分页的公开响应。
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.tenants.models import MemberRole


class TenantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120, title="企业名称")


class TenantPublic(BaseModel):
    id: UUID = Field(title="企业编号")
    name: str = Field(title="企业名称")
    role: MemberRole = Field(title="当前用户在该企业的角色")
    created_at: datetime = Field(title="企业创建时间")


class TenantPage(BaseModel):
    items: list[TenantPublic] = Field(title="当前用户加入的企业")
    next_cursor: UUID | None = Field(default=None, title="下一页游标，无后续时为空")


class MemberAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320, title="已注册用户邮箱")
    role: MemberRole = Field(default=MemberRole.MEMBER, title="成员角色")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class MemberRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: MemberRole = Field(title="新的成员角色")


class MemberPublic(BaseModel):
    id: UUID = Field(title="成员关系编号")
    tenant_id: UUID = Field(title="企业编号")
    user_id: UUID = Field(title="用户编号")
    email: str = Field(title="用户邮箱")
    role: MemberRole = Field(title="成员角色")
    created_at: datetime = Field(title="加入时间")


class MemberPage(BaseModel):
    items: list[MemberPublic] = Field(title="本企业成员")
    next_cursor: UUID | None = Field(default=None, title="下一页成员关系编号")
