# 用途：集中定义订阅允许的预约动作和消费时间判断，阻止取消后复活及跨周期消费。
from datetime import datetime

from app.core.errors import DomainError


def ensure_change_allowed(status: str, cancellation_pending: bool) -> None:
    if status != "active":
        raise DomainError("INVALID_SUBSCRIPTION_STATE", "当前订阅状态不允许预约变更", 409)
    if cancellation_pending:
        raise DomainError("CANCELLATION_SCHEDULED", "已预约到期取消，不能再预约套餐变更", 409)


def can_consume(
    *,
    status: str,
    cancel_pending: bool,
    cancel_effective_at: datetime | None,
    period_start: datetime,
    period_end: datetime,
    now: datetime,
) -> bool:
    if status != "active" or not period_start <= now < period_end:
        return False
    return not (cancel_pending and cancel_effective_at is not None and now >= cancel_effective_at)
