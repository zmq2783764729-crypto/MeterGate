# 用途：管理每次请求的独立编号与响应头，输出安全的完成或失败日志，并清理上下文。
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import log_request

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_context.get()


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)
        started_at = perf_counter()
        status_code = 500
        error_type = None

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            error_type = type(exc).__name__
            scope["state"]["error_code"] = "INTERNAL_ERROR"
            raise
        finally:
            try:
                log_request(
                    scope,
                    request_id=request_id,
                    status_code=status_code,
                    duration_ms=(perf_counter() - started_at) * 1000,
                    error_type=error_type,
                )
            finally:
                request_id_context.reset(token)
