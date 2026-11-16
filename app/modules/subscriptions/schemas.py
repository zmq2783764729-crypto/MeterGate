# 用途：限定订阅开通与预约请求字段，定义含周期快照、预约取消和消费前置状态的响应。
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.schemas import PlanVersionCreate


class SubscriptionActivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_version_id: UUID = Field(title="选择的具体套餐价格版本")


class SubscriptionPlanChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_version_id: UUID = Field(title="下周期选择的具体价格版本")


class PeriodTermsPublic(PlanVersionCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    period_id: UUID
    plan_version_id: UUID


class BillingPeriodPublic(BaseModel):
    id: UUID
    period_start: datetime
    period_end: datetime
    status: Literal["open", "closed"]
    terms: PeriodTermsPublic


class SubscriptionPublic(BaseModel):
    id: UUID
    tenant_id: UUID
    plan_version_id: UUID
    status: Literal["active", "canceled"]
    billing_anchor_day: int
    activated_at: datetime
    current_period: BillingPeriodPublic | None
    pending_plan_version_id: UUID | None
    pending_effective_at: datetime | None
    cancel_at_period_end: bool
    cancel_requested_at: datetime | None
    cancel_effective_at: datetime | None
    canceled_at: datetime | None
    can_consume: bool = Field(title="当前时刻是否满足订阅状态和周期消费前置条件")
