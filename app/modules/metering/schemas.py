# 用途：校验用量请求、规范化幂等摘要并定义后续扣量结果契约。
import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

MAX_USAGE_QUANTITY = 1_000_000
UsageMetric = Literal["data_query"]


class UsageIn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID = Field(title="调用方生成的用量事件编号")
    metric: UsageMetric = Field(title="用量指标")
    quantity: int = Field(strict=True, ge=1, le=MAX_USAGE_QUANTITY, title="本次用量")
    occurred_at: AwareDatetime = Field(title="事件发生时间，需携带时区")

    @field_validator("occurred_at", mode="before")
    @classmethod
    def parse_occurred_at(cls, value: object) -> object:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        raise ValueError("事件发生时间必须为带时区的 ISO 8601 时间")

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        try:
            return value.astimezone(UTC)
        except OverflowError as exc:
            raise ValueError("事件发生时间超出可表示范围") from exc


class UsageResult(BaseModel):
    event_id: UUID
    period_id: UUID
    metric: UsageMetric
    quantity: int
    used: int
    remaining: int
    replayed: bool = False


class UsageSummary(BaseModel):
    period_id: UUID
    metric: UsageMetric
    used: int
    hard_limit: int
    remaining: int
    currency: Literal["CNY"]
    estimated_total_cents: int
    estimate_only: Literal[True] = True


class UsageListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_id: UUID | None = None
    metric: UsageMetric = "data_query"
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None
    cursor: UUID | None = None
    limit: int = Field(default=20, ge=1, le=100)


class UsageEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    period_id: UUID
    metric: UsageMetric
    quantity: int
    occurred_at: datetime
    received_at: datetime


class UsageEventPage(BaseModel):
    items: list[UsageEventPublic]
    next_cursor: UUID | None = None


def canonical_payload_hash(command: UsageIn) -> str:
    # 按固定契约编码已校验字段，让键顺序、空白和等价时区写法得到同一摘要。
    payload = json.dumps(command.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()
