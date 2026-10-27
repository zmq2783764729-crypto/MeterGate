# MeterGate 代码文件用途汇总

> 更新时间：2026-10-23。与每个Python文件首行的 `# 用途：` 注释逐一对应。

当前共有 **61 个Python文件**。预留模块不能视为业务功能已实现。

## 已有实现及包入口

| 文件 | 文件首行用途说明 |
|---|---|
| [app/__init__.py](../app/__init__.py) | 标识 MeterGate 应用包并提供应用版本号。 |
| [app/api/__init__.py](../app/api/__init__.py) | 标识 HTTP 接口包，包含健康检查及健康与认证路由的汇总入口。 |
| [app/api/health.py](../app/api/health.py) | 提供 live 存活检查和 PostgreSQL/Redis 的 ready 就绪检查，故障时返回 503 且隐藏凭据。 |
| [app/api/router.py](../app/api/router.py) | 为独立应用工厂复制已声明的 HTTP 接口，保持依赖覆盖与应用配置隔离。 |
| [app/core/__init__.py](../app/core/__init__.py) | 标识核心配置包，当前包含环境配置模块。 |
| [app/core/config.py](../app/core/config.py) | 读取 MG_ 环境变量和本项目 .env，校验配置并隐藏数据库地址与密钥的显示值。 |
| [app/core/errors.py](../app/core/errors.py) | 定义领域错误并统一中文错误响应，关联请求编号且隐藏原始异常和敏感输入。 |
| [app/core/logging.py](../app/core/logging.py) | 配置安全的 JSON 日志，仅输出允许的请求元数据并阻止访问日志和异常文本泄露敏感值。 |
| [app/core/security.py](../app/core/security.py) | 使用 Argon2 哈希验证密码，并按固定算法、签发方、接收方和期限签发校验访问令牌。 |
| [app/db/__init__.py](../app/db/__init__.py) | 标识数据库包，提供模型基类、异步连接池和请求会话管理。 |
| [app/db/base.py](../app/db/base.py) | 提供 SQLAlchemy 模型基类，供后续业务模型与 Alembic 共享表结构元数据。 |
| [app/db/session.py](../app/db/session.py) | 创建 PostgreSQL 异步连接池和会话工厂，为每次请求提供独立会话且不自动提交事务。 |
| [app/dependencies/__init__.py](../app/dependencies/__init__.py) | 标识依赖注入包，提供登录用户认证、租户成员身份和角色权限校验。 |
| [app/dependencies/auth.py](../app/dependencies/auth.py) | 注入认证配置，验证 Bearer 访问令牌，并从数据库加载当前登录用户。 |
| [app/dependencies/permissions.py](../app/dependencies/permissions.py) | 提供可复用角色依赖，在可信租户上下文基础上限制接口允许的成员角色。 |
| [app/dependencies/tenant.py](../app/dependencies/tenant.py) | 将URL企业编号与已认证用户的数据库成员关系匹配，生成可信租户上下文。 |
| [app/main.py](../app/main.py) | 在模块顶层使用 @app 定义接口，并配置应用工厂、错误处理、日志及数据库和 Redis 生命周期。 |
| [app/middleware/__init__.py](../app/middleware/__init__.py) | 标识请求上下文中间件包，提供请求编号管理。 |
| [app/middleware/request_context.py](../app/middleware/request_context.py) | 管理每次请求的独立编号与响应头，输出安全的完成或失败日志，并清理上下文。 |
| [app/modules/__init__.py](../app/modules/__init__.py) | 标识业务模块包，为企业、订阅、计量和结算功能预留分层目录。 |
| [app/modules/auth/__init__.py](../app/modules/auth/__init__.py) | 标识用户认证业务包，包含用户模型、注册登录分层实现与公开响应结构。 |
| [app/modules/auth/models.py](../app/modules/auth/models.py) | 定义用户表，保存唯一邮箱、密码哈希、UUID 主键和带时区的创建时间。 |
| [app/modules/auth/repository.py](../app/modules/auth/repository.py) | 通过异步会话查询和添加用户，写入时 flush 但不自行提交事务。 |
| [app/modules/auth/router.py](../app/modules/auth/router.py) | 提供 main.py 顶层认证接口调用的处理函数，以及会话和配置依赖类型。 |
| [app/modules/auth/schemas.py](../app/modules/auth/schemas.py) | 校验注册登录输入、统一邮箱大小写，并定义不含密码哈希的用户与令牌响应。 |
| [app/modules/auth/service.py](../app/modules/auth/service.py) | 编排用户注册和密码认证，管理注册事务并将邮箱唯一冲突转换为业务错误。 |
| [app/modules/tenants/__init__.py](../app/modules/tenants/__init__.py) | 标识企业业务包，提供企业创建、租户上下文、成员管理和管理员保护。 |
| [app/modules/tenants/context.py](../app/modules/tenants/context.py) | 提供不可变租户上下文，携带经过数据库成员关系验证的企业、用户和角色。 |
| [app/modules/tenants/models.py](../app/modules/tenants/models.py) | 定义企业和成员关系表，通过外键、角色检查与联合唯一约束保护成员数据。 |
| [app/modules/tenants/repository.py](../app/modules/tenants/repository.py) | 按用户或可信租户上下文访问企业成员数据，并提供管理操作的企业行锁与管理员计数。 |
| [app/modules/tenants/router.py](../app/modules/tenants/router.py) | 为main.py企业与成员接口提供处理函数、租户和角色依赖以及独立业务会话。 |
| [app/modules/tenants/schemas.py](../app/modules/tenants/schemas.py) | 校验企业和成员请求，定义企业、成员及items/next_cursor分页的公开响应。 |
| [app/modules/tenants/service.py](../app/modules/tenants/service.py) | 编排企业与成员管理事务，复核管理员权限并通过企业行锁保护最后一位管理员。 |
| [migrations/env.py](../migrations/env.py) | 读取应用配置与模型元数据，通过异步 PostgreSQL 连接执行 Alembic 迁移或输出 SQL。 |
| [migrations/versions/0001_baseline_initialize_migration_baseline.py](../migrations/versions/0001_baseline_initialize_migration_baseline.py) | initialize migration baseline；记录本次表结构升级与回退操作。 |
| [migrations/versions/0002_users_create_users_table.py](../migrations/versions/0002_users_create_users_table.py) | 创建 users 表与邮箱唯一约束，回退时删除用户表。 |
| [migrations/versions/0003_tenants_create_tenants_and_memberships.py](../migrations/versions/0003_tenants_create_tenants_and_memberships.py) | 创建企业及成员关系表、外键、角色检查和联合唯一约束，回退时按依赖逆序删除。 |
| [tests/test_app.py](../tests/test_app.py) | 验证应用配置互不串用、健康响应与配置显示不泄露测试密钥，以及生命周期正常结束。 |
| [tests/test_auth_database.py](../tests/test_auth_database.py) | 在专属 PostgreSQL 测试库验证注册登录、真实唯一约束并发冲突、令牌身份和敏感值隐藏。 |
| [tests/test_auth_security.py](../tests/test_auth_security.py) | 验证 Argon2 密码、邮箱输入和 JWT 的签名、声明、算法白名单与认证配置边界。 |
| [tests/test_db_runtime.py](../tests/test_db_runtime.py) | 验证就绪检查的故障、超时与脱敏行为，以及连接资源在正常和异常路径下正确释放。 |
| [tests/test_error_contract.py](../tests/test_error_contract.py) | 验证领域、HTTP、参数和未知错误的统一响应、请求编号一致性及敏感内容隐藏。 |
| [tests/test_member_contract.py](../tests/test_member_contract.py) | 验证成员输入边界与四个成员接口的未认证401响应，避免暴露租户数据。 |
| [tests/test_member_database.py](../tests/test_member_database.py) | 在专属PostgreSQL库验证跨租户授权、角色即时生效及并发修改下最后管理员保护。 |
| [tests/test_request_context.py](../tests/test_request_context.py) | 验证请求编号在成功与错误响应中一致可查、每请求唯一、并发隔离且异常后正确清理。 |
| [tests/test_request_logging.py](../tests/test_request_logging.py) | 验证请求与错误日志的编号关联、并发隔离、字段安全、日志级别及重复配置行为。 |
| [tests/test_response_language.py](../tests/test_response_language.py) | 验证中文健康状态、接口说明和错误提示，并确保参数与内部异常不泄露到响应。 |
| [tests/test_tenant_contract.py](../tests/test_tenant_contract.py) | 验证企业名称与额外字段校验，以及企业接口在缺少有效身份时返回统一401错误。 |
| [tests/test_tenant_database.py](../tests/test_tenant_database.py) | 在专属PostgreSQL库验证企业管理员创建、用户隔离、游标分页、失败回滚及真实成员约束。 |

迁移配套文件：alembic.ini指定目录和日志，migrations/script.py.mako提供版本模板。0001_baseline为基线，0002_users创建用户，0003_tenants创建企业和成员关系。第06天不改变表结构。

## 预留模块

| 文件 | 文件首行用途说明 |
|---|---|
| [app/integrations/__init__.py](../app/integrations/__init__.py) | 预留支付等外部服务的适配器包，尚未实现。 |
| [app/integrations/payments/__init__.py](../app/integrations/payments/__init__.py) | 预留支付提供方接口及模拟支付适配器包，尚未实现。 |
| [app/modules/api_keys/__init__.py](../app/modules/api_keys/__init__.py) | 预留企业 API Key 的创建、权限范围、到期和撤销业务模块，尚未实现。 |
| [app/modules/audit/__init__.py](../app/modules/audit/__init__.py) | 预留关键业务操作的审计记录和审计查询模块，尚未实现。 |
| [app/modules/billing/__init__.py](../app/modules/billing/__init__.py) | 预留周期计价、账单生成、账单查询和对账业务模块，尚未实现。 |
| [app/modules/catalog/__init__.py](../app/modules/catalog/__init__.py) | 预留套餐及不可变价格版本管理业务模块，尚未实现。 |
| [app/modules/demo/__init__.py](../app/modules/demo/__init__.py) | 预留服务端计量的数据查询演示接口及结果重放业务模块，尚未实现。 |
| [app/modules/metering/__init__.py](../app/modules/metering/__init__.py) | 预留用量事件、幂等接收、并发额度扣减和用量查询业务模块，尚未实现。 |
| [app/modules/payments/__init__.py](../app/modules/payments/__init__.py) | 预留支付会话、回调验签、回调幂等和账单付款状态业务模块，尚未实现。 |
| [app/modules/subscriptions/__init__.py](../app/modules/subscriptions/__init__.py) | 预留订阅状态、计费周期、套餐变更和取消业务模块，尚未实现。 |
| [app/observability/__init__.py](../app/observability/__init__.py) | 预留运行指标及其他可观测性功能包，尚未实现。 |
| [app/workers/__init__.py](../app/workers/__init__.py) | 预留后台任务、消息代理和事务 Outbox 执行包，尚未实现。 |

## 建议阅读顺序

1. app/main.py：顶层@app接口、应用创建和生命周期；app/api/router.py：工厂复制接口。
2. app/dependencies/auth.py → tenant.py → permissions.py：从用户到租户角色的验证流程。
3. app/modules/tenants/context.py：业务层使用的可信租户上下文。
4. app/modules/tenants/service.py → repository.py：权限复核、行锁、管理员保护与租户过滤。
5. [第06天代码讲解](day06-practice.md)与[逐行Postman测试集](day06-test-cases.md)。

实现进度只在[progress.md](../progress.md)维护，本文件汇总代码职责，不另建进度体系。
