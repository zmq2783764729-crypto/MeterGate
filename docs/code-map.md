# MeterGate 代码文件用途汇总

> 更新时间：2026-10-15。与每个 Python 文件首行的 `# 用途：` 注释逐一对应。

当前共有 **38 个 Python 文件**。其中标记为“预留”的文件只有包占位，不能视为业务功能已经实现。

## 已有实现及包入口

| 文件 | 文件首行用途说明 |
|---|---|
| [app/__init__.py](../app/__init__.py) | 标识 MeterGate 应用包并提供应用版本号。 |
| [app/api/__init__.py](../app/api/__init__.py) | 标识 HTTP 接口包，当前包含健康检查接口和路由汇总。 |
| [app/api/health.py](../app/api/health.py) | 提供 live 存活检查和 PostgreSQL/Redis 的 ready 就绪检查，故障时返回 503 且隐藏凭据。 |
| [app/api/router.py](../app/api/router.py) | 汇总并注册 HTTP 路由，当前只挂载健康检查接口。 |
| [app/core/__init__.py](../app/core/__init__.py) | 标识核心配置包，当前包含环境配置模块。 |
| [app/core/config.py](../app/core/config.py) | 读取 MG_ 环境变量和本项目 .env，校验配置并隐藏数据库地址与密钥的显示值。 |
| [app/core/errors.py](../app/core/errors.py) | 定义领域错误并统一中文错误响应，关联请求编号且隐藏原始异常和敏感输入。 |
| [app/core/logging.py](../app/core/logging.py) | 配置安全的 JSON 日志，仅输出允许的请求元数据并阻止访问日志和异常文本泄露敏感值。 |
| [app/main.py](../app/main.py) | 创建 FastAPI 应用，配置安全日志、请求编号和中文错误处理，并管理数据库与 Redis 资源。 |
| [app/middleware/__init__.py](../app/middleware/__init__.py) | 标识请求上下文中间件包，提供请求编号管理。 |
| [app/middleware/request_context.py](../app/middleware/request_context.py) | 管理每次请求的独立编号与响应头，输出安全的完成或失败日志，并清理上下文。 |
| [app/db/__init__.py](../app/db/__init__.py) | 标识数据库包，提供模型基类、异步连接池和请求会话管理。 |
| [app/db/base.py](../app/db/base.py) | 提供 SQLAlchemy 模型基类，供后续业务模型与 Alembic 共享表结构元数据。 |
| [app/db/session.py](../app/db/session.py) | 创建 PostgreSQL 异步连接池和会话工厂，为每次请求提供独立会话且不自动提交事务。 |
| [tests/test_app.py](../tests/test_app.py) | 验证应用配置互不串用、健康响应与配置显示不泄露测试密钥，以及生命周期正常结束。 |
| [tests/test_db_runtime.py](../tests/test_db_runtime.py) | 验证就绪检查的故障、超时与脱敏行为，以及连接资源在正常和异常路径下正确释放。 |
| [tests/test_response_language.py](../tests/test_response_language.py) | 验证中文健康状态、接口说明和错误提示，并确保参数与内部异常不泄露到响应。 |
| [tests/test_request_context.py](../tests/test_request_context.py) | 验证请求编号在成功与错误响应中一致可查、每请求唯一、并发隔离且异常后正确清理。 |
| [tests/test_error_contract.py](../tests/test_error_contract.py) | 验证领域、HTTP、参数和未知错误的统一响应、请求编号一致性及敏感内容隐藏。 |
| [tests/test_request_logging.py](../tests/test_request_logging.py) | 验证请求与错误日志的编号关联、并发隔离、字段安全、日志级别及重复配置行为。 |
| [migrations/env.py](../migrations/env.py) | 读取应用配置与模型元数据，通过异步 PostgreSQL 连接执行 Alembic 迁移或输出 SQL。 |
| [migrations/versions/0001_baseline_initialize_migration_baseline.py](../migrations/versions/0001_baseline_initialize_migration_baseline.py) | initialize migration baseline；记录本次表结构升级与回退操作。 |

迁移配套文件：`alembic.ini` 指定目录和日志，数据库地址从应用配置读取；`migrations/script.py.mako` 为后续生成的版本文件提供模板与用途注释。首次迁移 0001_baseline 已生成并执行，只记录版本基线，尚未创建业务表。

## 预留模块

| 文件 | 文件首行用途说明 |
|---|---|
| [app/dependencies/__init__.py](../app/dependencies/__init__.py) | 预留用户身份、租户上下文和权限校验的依赖注入包，尚未实现。 |
| [app/integrations/__init__.py](../app/integrations/__init__.py) | 预留支付等外部服务的适配器包，尚未实现。 |
| [app/integrations/payments/__init__.py](../app/integrations/payments/__init__.py) | 预留支付提供方接口及模拟支付适配器包，尚未实现。 |
| [app/modules/__init__.py](../app/modules/__init__.py) | 标识业务模块包，为企业、订阅、计量和结算功能预留分层目录。 |
| [app/modules/api_keys/__init__.py](../app/modules/api_keys/__init__.py) | 预留企业 API Key 的创建、权限范围、到期和撤销业务模块，尚未实现。 |
| [app/modules/audit/__init__.py](../app/modules/audit/__init__.py) | 预留关键业务操作的审计记录和审计查询模块，尚未实现。 |
| [app/modules/auth/__init__.py](../app/modules/auth/__init__.py) | 预留用户注册、密码登录和访问令牌相关业务模块，尚未实现。 |
| [app/modules/billing/__init__.py](../app/modules/billing/__init__.py) | 预留周期计价、账单生成、账单查询和对账业务模块，尚未实现。 |
| [app/modules/catalog/__init__.py](../app/modules/catalog/__init__.py) | 预留套餐及不可变价格版本管理业务模块，尚未实现。 |
| [app/modules/demo/__init__.py](../app/modules/demo/__init__.py) | 预留服务端计量的数据查询演示接口及结果重放业务模块，尚未实现。 |
| [app/modules/metering/__init__.py](../app/modules/metering/__init__.py) | 预留用量事件、幂等接收、并发额度扣减和用量查询业务模块，尚未实现。 |
| [app/modules/payments/__init__.py](../app/modules/payments/__init__.py) | 预留支付会话、回调验签、回调幂等和账单付款状态业务模块，尚未实现。 |
| [app/modules/subscriptions/__init__.py](../app/modules/subscriptions/__init__.py) | 预留订阅状态、计费周期、套餐变更和取消业务模块，尚未实现。 |
| [app/modules/tenants/__init__.py](../app/modules/tenants/__init__.py) | 预留企业租户、成员关系和角色管理业务模块，尚未实现。 |
| [app/observability/__init__.py](../app/observability/__init__.py) | 预留运行指标及其他可观测性功能包，尚未实现。 |
| [app/workers/__init__.py](../app/workers/__init__.py) | 预留后台任务、消息代理和事务 Outbox 执行包，尚未实现。 |

## 建议阅读顺序

1. `app/main.py`：了解应用如何创建和启动。
2. `app/core/config.py`：了解配置从哪里读取。
3. `app/api/router.py` → `app/api/health.py`：了解路由与接口的关系。
4. `tests/test_app.py`：了解现有验证范围。
5. 按 [开发计划](plan.md)逐步实现预留模块，并同步更新文件首行注释与本汇总。

实现进度只在 [progress.md](../progress.md) 维护，本文件汇总代码职责，不另建进度体系。
