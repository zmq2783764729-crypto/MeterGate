# 用途：严格校验整数分金额和正整数额度，并定义套餐、历史版本与分页公开响应。
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt

MAX_BIGINT = 2**63 - 1
MoneyCents = Annotated[StrictInt, Field(ge=0, le=MAX_BIGINT)]
PositiveQuota = Annotated[StrictInt, Field(gt=0, le=MAX_BIGINT)]


class PlanVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Literal["CNY"] = "CNY"
    billing_interval: Literal["month"] = "month"
    base_fee_cents: MoneyCents = Field(title="基础月费（分）")
    unit_price_cents: MoneyCents = Field(title="每次成功调用单价（分）")
    hard_limit: PositiveQuota = Field(title="周期硬额度（次数）")


class PlanVersionPublic(PlanVersionCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    plan_id: UUID
    version: int
    created_at: datetime


class PlanPublic(BaseModel):
    id: UUID
    code: str
    name: str
    latest_version: PlanVersionPublic


class PlanPage(BaseModel):
    items: list[PlanPublic]
    next_cursor: UUID | None = None


class PlanVersionPage(BaseModel):
    items: list[PlanVersionPublic]
    next_cursor: int | None = None
