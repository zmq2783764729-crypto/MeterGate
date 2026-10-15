# 用途：配置安全的 JSON 日志，仅输出允许的请求元数据并阻止访问日志和异常文本泄露敏感值。
import json
import logging
from datetime import UTC, datetime
from typing import TextIO

from starlette.types import Scope

EVENT_MESSAGES = {
    "request_completed": "请求处理完成",
    "request_failed": "请求处理失败",
    "server_event": "服务器事件",
    "application_event": "应用事件",
}
SAFE_FIELDS = (
    "request_id",
    "method",
    "route",
    "status_code",
    "duration_ms",
    "error_type",
    "code",
)
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", None)
        if not isinstance(event, str) or event not in EVENT_MESSAGES:
            event = "server_event" if record.name.startswith("uvicorn") else "application_event"
        timestamp = datetime.fromtimestamp(record.created, UTC)
        payload = {
            "timestamp": timestamp.isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "event": event,
            "message": EVENT_MESSAGES[event],
        }
        for field in SAFE_FIELDS:
            value = getattr(record, field, None)
            if isinstance(value, (str, int, float, bool)):
                payload[field] = value
        if record.exc_info and record.exc_info[0] is not None and "error_type" not in payload:
            payload["error_type"] = record.exc_info[0].__name__
        # 不调用 getMessage/formatException：它们可能展开口令、参数、异常文本或调用栈。
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str, *, stream: TextIO | None = None) -> None:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    for name in ("metergate", "uvicorn.error"):
        logger = logging.getLogger(name)
        old_handlers = logger.handlers[:]
        logger.handlers = [handler]
        logger.setLevel(level)
        logger.propagate = False
        logger.disabled = False
        for old in old_handlers:
            if isinstance(old.formatter, JsonFormatter):
                old.close()

    # 默认访问日志会展开原始 URL 和查询参数，改由应用中间件输出安全的请求日志。
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = []
    access_logger.propagate = False
    access_logger.disabled = True


def log_request(
    scope: Scope,
    *,
    request_id: str,
    status_code: int,
    duration_ms: float,
    error_type: str | None,
) -> None:
    route = getattr(scope.get("route"), "path", None)
    method = scope.get("method", "")
    event = "request_failed" if error_type is not None else "request_completed"
    level = (
        logging.ERROR
        if error_type is not None or status_code >= 500
        else logging.WARNING
        if status_code >= 400
        else logging.INFO
    )
    logging.getLogger("metergate.http").log(
        level,
        event,
        extra={
            "event": event,
            "request_id": request_id,
            "method": method if method in HTTP_METHODS else "OTHER",
            "route": route if isinstance(route, str) else "<unmatched>",
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "error_type": error_type,
            "code": scope.get("state", {}).get("error_code"),
        },
    )
