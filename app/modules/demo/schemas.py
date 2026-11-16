# 用途：定义按名称查询套餐的请求及可重放的查询结果。
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.metering.schemas import UsageResult


class DataQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    limit: int = Field(default=10, strict=True, ge=1, le=20)


class DataQueryItem(BaseModel):
    code: str
    name: str


class DataQueryResult(BaseModel):
    items: list[DataQueryItem]
    usage: UsageResult
