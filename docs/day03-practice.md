# 第 03 天动手练习：错误、请求编号与日志

实际进度只在根目录 progress.md 维护。本日依次学习请求编号、统一错误响应、结构化日志。用户已依次确认三项练习完成，结合既有自动验证，第 03 天通过。以下保留操作步骤供复习；用户后续手动接口测试统一使用 Postman，操作说明不再提供 PowerShell 测试命令。

## 练习 1：观察每次请求的编号

当多人同时调用接口时，需要一个编号把某次请求、错误响应和日志关联起来。请求编号练习已由用户验证通过；当前已进一步实现错误响应体的统一格式，结构化日志是后续练习。

### 代码阅读顺序

1. `app/middleware/request_context.py`：中间件在路由前运行，`uuid4().hex` 为每次 HTTP 请求生成编号，存入 request.state；本阶段始终使用服务端生成的新编号。
2. `ContextVar`：让当前异步上下文读取同一个编号，并发请求各自隔离。`set()` 返回旧上下文标记，`finally` 中用 `reset(token)` 复原，避免正常结束或异常后串用。参考：[Python contextvars](https://docs.python.org/3/library/contextvars.html)。
3. `send_with_request_id()`：在响应头开始发送时写入编号，成功响应和框架已处理的错误响应都会经过这里。
4. `app/main.py`：在 create_app 中注册中间件，不改变数据库连接与迁移。
5. `app/core/errors.py`：未知异常由外层 ServerErrorMiddleware 生成 500 响应，因此额外从 request.state 补上同一个响应头；保留原有中文错误及敏感内容隐藏行为。

### Postman 复验方式

保持 FastAPI 运行，在 Postman 使用 GET 请求 `http://127.0.0.1:8000/health/live`，连续发送两次。在响应区 Headers 中观察 X-Request-ID：每次都有编号，两次不同；健康响应体没有新增外层包装。

HTTP 响应头不区分大小写，因此显示 `x-request-id` 或 `X-Request-ID` 都正常。若应用未加载最新代码，重启已有开发服务后再测试。

### 助手测试

新增 7 项请求上下文测试，连同原有 11 项共 18 passed。覆盖正常/404/503、服务端独立编号、8 个并发请求隔离、422、未知异常 500 以及异常后的上下文清理。仅测试内临时注册验证路由，正式应用没有增加测试故障接口。

## 练习 2：统一错误响应

### 代码如何工作

1. `app/core/errors.py` 的 DomainError 表达预期业务失败，携带 code、中文 message 和 HTTP status_code。后续业务层可以抛出它，不必自行拼 HTTP 响应。
2. `_error_response()` 是所有异常处理器的公共出口，使用 request.state 中的编号，生成 ErrorResponse，并把同一编号写入响应头。
3. HTTP 错误、参数校验和未知异常统一为 code/message/request_id。422 可附加 errors 数组，只含字段位置和中文说明，不返回原始输入、校验异常或密码值。
4. main.py 注册 DomainError 处理器；未知错误返回通用中文提示。WWW-Authenticate、Allow、Retry-After 等必要 HTTP 头保留。
5. 成功响应继续直接返回业务 Schema。ready 的 503 是专门的健康检查报告，保留既有 status/checks 结构；异常处理器不会改写所有非 2xx 响应。

### Postman 操作

保持 FastAPI 运行；Auth 选择 No Auth，不需要额外 Headers，Body 选择 none。

| 方法 | URL | 预期 |
|---|---|---|
| GET | http://127.0.0.1:8000/not-exist | 404，code 为 NOT_FOUND |
| POST | http://127.0.0.1:8000/health/live | 405，code 为 METHOD_NOT_ALLOWED，响应头 Allow 包含 GET |
| GET | http://127.0.0.1:8000/health/live | 200，健康响应体保持原样 |

404 的响应体示例（编号每次不同）：

```json
{
  "code": "NOT_FOUND",
  "message": "请求的接口或资源不存在",
  "request_id": "本次请求生成的编号"
}
```

查看响应区 Headers，将 X-Request-ID 与 JSON 中的 request_id 比较，应完全相同。

可以在该 404 请求的 Scripts → Post-response 添加断言：

```javascript
pm.test("返回 404", function () {
  pm.response.to.have.status(404);
});
pm.test("错误体与响应头编号一致", function () {
  pm.expect(pm.response.json().request_id)
    .to.eql(pm.response.headers.get("X-Request-ID"));
});
```

参考：[Postman 响应断言](https://learning.postman.com/docs/tests-and-scripts/write-scripts/postman-sandbox-reference/pm-response/)。把响应和断言结果反馈给助手，接着实现日志。

### 自动验证

完整测试 24 passed：包含领域错误 409、缺少认证 401、参数错误 422、未知错误 500、404、405、请求编号一致及敏感输入隐藏。401/422/500 的触发路由仅在测试中注册，正式应用没有为教学暴露故障接口；后续真实认证业务在第 04 天实现。

## 练习 3：结构化日志与请求追踪

### 代码如何工作

1. `app/core/logging.py`：使用标准 logging 和 JsonFormatter，每条请求日志输出一行 JSON。只允许固定元数据字段，不展开任意日志消息、参数、原始异常文本或调用栈。
2. `app/main.py`：lifespan 启动时按 Settings.log_level 配置日志。默认 INFO；正常请求为 INFO，4xx 为 WARNING，5xx 或未处理异常为 ERROR。
3. `app/middleware/request_context.py`：记录请求耗时与实际响应状态，异常时只记录异常类型；输出日志后清理 ContextVar。错误处理器保存 error_code，方便日志与错误体关联。
4. 日志的 route 使用注册的路由模板，例如 `/items/{item_id}`，不记录参数值；未匹配路径显示 `<unmatched>`。查询参数、请求体、认证头不进入日志。
5. 默认 Uvicorn 访问日志会包含原始 URL，因此关闭该日志，由中间件输出请求记录；Uvicorn 错误日志使用安全 JSON 格式，只保留异常类型。启动早期与重载器仍可能输出普通启动提示，这些提示不是请求日志。
6. 重复配置不会累加请求日志处理器，不改写 Python 根日志处理器。日志配置是进程级配置，应用启动时应用一次。

### Postman 操作

保持 FastAPI 运行，在响应区查看编号，在运行 FastAPI 的窗口或 IDE Console 查看服务端日志。MG_LOG_LEVEL 使用默认 INFO 即可；若此前调高了等级，正常请求日志会被过滤，修改配置后需要重启应用。

| 请求 | Postman 设置 | 预期 |
|---|---|---|
| GET http://127.0.0.1:8000/health/live | No Auth，Body none | 200；响应头 X-Request-ID 对应一条 INFO 日志 |
| GET http://127.0.0.1:8000/not-exist?token=demo-token | No Auth；手动 Headers：Authorization 为 Bearer demo-jwt，X-API-Key 为 demo-api-key；Body none | 404；错误体、响应头、WARNING 日志的编号一致；日志没有这些演示值 |
| POST http://127.0.0.1:8000/health/live | No Auth；Body 选 raw → JSON，填写下面的示例 | 405；日志包含状态与错误码，不包含密码值 |

第三个请求的 Body：

```json
{"password": "demo-password"}
```

正常请求的日志示例（编号、时间和耗时以实际结果为准）：

```json
{
  "timestamp": "2026-10-15T02:00:00.000+00:00",
  "level": "INFO",
  "event": "request_completed",
  "message": "请求处理完成",
  "request_id": "与Postman响应头一致的编号",
  "method": "GET",
  "route": "/health/live",
  "status_code": 200,
  "duration_ms": 1.23
}
```

`request_completed` 表示请求处理流程结束；业务结果看 status_code 和可选的 code。未知异常产生 request_failed，含异常类型 error_type，不含原始异常说明。日志时间统一使用 UTC。

### 助手已验证

- 完整测试 33 passed：新增日志关联、并发隔离、敏感参数隐藏、服务器错误日志安全、配置幂等与等级过滤。
- 独立临时 Uvicorn 验证 200/500/422/401/404：响应编号与 JSON 日志一致；完整服务器输出不含演示口令、JWT、API Key、路径值、查询值或原始异常文本。
- 验收服务使用单独端口及忽略目录中的临时路由，结束后已停止；没有向正式应用添加故障接口，没有停止用户服务或容器。

用户已反馈最终日志输出完成，第 03 天收尾。分页接口未来统一使用 items/next_cursor，当前尚未实现列表业务。

## Git 同步核对

本次开始时，本地 HEAD 为 dd4838e，标题为完成第 02 天，但 git status 仍列出 alembic.ini、数据库连接、迁移等关键文件未跟踪；不能仅凭提交标题认定新增文件都已包含。换电脑前需把应共享的新文件加入 Git 并提交。本阶段没有自动暂存或推送，用户 .idea/ 保持原样。
