# 用途：定义领域错误并统一中文错误响应，关联请求编号且隐藏原始异常和敏感输入。
from collections.abc import Mapping
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

HTTP_MESSAGES = {
    400: "请求格式不正确",
    401: "请先登录或提供有效的身份凭据",
    403: "没有权限执行此操作",
    404: "请求的接口或资源不存在",
    405: "此接口不支持该请求方法",
    409: "请求与当前资源状态冲突",
    422: "请求参数校验失败",
    429: "请求过于频繁，请稍后重试",
    500: "服务内部错误，请稍后重试",
    503: "服务暂时不可用，请稍后重试",
}

HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.headers = headers


class ErrorResponse(BaseModel):
    code: str = Field(title="错误码")
    message: str = Field(title="错误说明")
    request_id: str = Field(title="请求编号")
    errors: list[dict[str, str]] | None = Field(default=None, title="参数错误明细")


def _error_response(
    request: Request,
    *,
    code: str,
    message: str,
    status_code: int,
    headers: Mapping[str, str] | None = None,
    errors: list[dict[str, str]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = uuid4().hex
        request.state.request_id = request_id
    request.state.error_code = code
    payload = ErrorResponse(code=code, message=message, request_id=request_id, errors=errors)
    response = JSONResponse(
        payload.model_dump(exclude_none=True), status_code=status_code, headers=headers
    )
    # 外层 500 处理也走同一入口，保证错误体与响应头始终使用同一个编号。
    response.headers["X-Request-ID"] = request_id
    return response


def domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return _error_response(
        request,
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        headers=exc.headers,
    )


def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    # 保留业务代码明确提供的中文提示；框架英文提示改用中文状态说明。
    if not isinstance(detail, str) or not any("\u4e00" <= char <= "\u9fff" for char in detail):
        detail = HTTP_MESSAGES.get(exc.status_code, "请求处理失败")
    return _error_response(
        request,
        code=HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}"),
        message=detail,
        status_code=exc.status_code,
        headers=exc.headers,
    )


def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": "缺少必填参数" if error["type"] == "missing" else "参数格式或取值不正确",
        }
        for error in exc.errors()
    ]
    return _error_response(
        request,
        code="VALIDATION_ERROR",
        message=HTTP_MESSAGES[422],
        status_code=422,
        errors=errors,
    )


def internal_error(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        request, code="INTERNAL_ERROR", message=HTTP_MESSAGES[500], status_code=500
    )
