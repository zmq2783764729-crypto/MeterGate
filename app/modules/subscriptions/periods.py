# 用途：提供UTC时钟、保留账单日锚点的日历月边界，以及左闭右开周期归属判断。
from calendar import monthrange
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def next_month_boundary(start: datetime, anchor_day: int) -> datetime:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("周期时间必须带时区")
    if not 1 <= anchor_day <= 31:
        raise ValueError("账单日必须在1到31之间")
    start = start.astimezone(UTC)
    year, month = (start.year + 1, 1) if start.month == 12 else (start.year, start.month + 1)
    day = min(anchor_day, monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def contains_instant(start: datetime, end: datetime, instant: datetime) -> bool:
    for value in (start, end, instant):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("周期时间必须带时区")
    return start <= instant < end
