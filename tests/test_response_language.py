# 用途：验证中文健康状态、接口说明和错误提示，并确保参数与内部异常不泄露到响应。
import json

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app.api.health import LiveResponse, ReadyResponse
from app.core.config import Settings
from app.core.errors import http_error, internal_error, validation_error
from app.main import create_app


def test_health_response_and_openapi_use_chinese():
    response = ReadyResponse(status="已就绪", checks={"database": "正常", "redis": "正常"})
    assert json.loads(response.model_dump_json())["status"] == "已就绪"
    assert LiveResponse(status="正常", service="MeterGate", version="0.1.0").status == "正常"
    application = create_app(Settings(_env_file=None))
    schema = application.openapi()
    assert schema["info"]["description"] == "MeterGate 企业服务计量与结算接口"
    assert schema["paths"]["/health/ready"]["get"]["summary"] == "检查服务是否就绪"
    assert schema["components"]["schemas"]["ReadyResponse"]["properties"]["status"]["enum"] == [
        "已就绪",
        "未就绪",
    ]


def test_http_errors_use_chinese_and_preserve_status_and_headers():
    request = Request({"type": "http"})
    response = http_error(request, HTTPException(405, headers={"Allow": "GET"}))
    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert json.loads(response.body)["message"] == "此接口不支持该请求方法"
    response = http_error(request, HTTPException(404))
    assert json.loads(response.body)["message"] == "请求的接口或资源不存在"
    response = http_error(request, HTTPException(503, "数据库尚未配置"))
    assert json.loads(response.body)["message"] == "数据库尚未配置"


def test_validation_and_internal_errors_do_not_expose_raw_inputs():
    request = Request({"type": "http"})
    exception = RequestValidationError(
        [
            {"loc": ("query", "limit"), "type": "missing", "msg": "Field required"},
            {
                "loc": ("body", "password"),
                "type": "value_error",
                "msg": "synthetic-private-value",
                "input": "synthetic-private-value",
            },
        ]
    )
    response = validation_error(request, exception)
    assert response.status_code == 422
    content = json.loads(response.body)
    assert content["message"] == "请求参数校验失败"
    assert content["errors"][0]["message"] == "缺少必填参数"
    assert content["errors"][1]["message"] == "参数格式或取值不正确"
    assert b"synthetic-private-value" not in response.body
    response = internal_error(request, RuntimeError("synthetic-private-value"))
    assert response.status_code == 500
    assert json.loads(response.body)["message"] == "服务内部错误，请稍后重试"
    assert b"synthetic-private-value" not in response.body
